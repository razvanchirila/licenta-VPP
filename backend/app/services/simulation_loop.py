"""
Live simulation on top of vpp_core: one simulated step (dt_h, default 15 min) per real tick.
Step order (SimulationLoop._step): community from the DB -> scenario slice (PV, prices) + load from the
switched-on devices -> controller dispatch -> batteries -> P2P trades -> persist in one transaction ->
advance clock and broadcast. With SIM_DATA=real the simulated calendar day is mapped to the same day of
the data: PV from 2023, prices from SIM_PRICE_YEAR; otherwise both come from the synthetic generator.
The MPC forecasts from Observations, the readings of the steps already simulated (restored from house_steps
after a restart), and from the prices published for today and, after 13:00, tomorrow.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

import numpy as np
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session_context
from app.db.models import (
    BatteryModel,
    DeviceModel,
    EnergyLogModel,
    HouseModel,
    HouseStepModel,
    SimulationStateModel,
    TradeTransactionModel,
    VPPReserveModel,
    WalletModel,
    WalletTransactionModel,
)
from app.db.repositories import HouseRepository
from app.services.device_load import DeviceProfiles, house_load
from app.services.settlement import SettlementService, Trade
from app.settings import settings
from vpp_core import data_sources as ds
from vpp_core.battery import Battery
from vpp_core.controllers import RuleBasedController
from vpp_core.dispatch import FLOWS, Dispatch
from vpp_core.forecast import HISTORY_DAYS, History, published_steps
from vpp_core.optimizer import RealisticMPCController
from vpp_core.params import BatteryParams, CommunityParams, GridParams, HouseParams
from vpp_core.scenario import Scenario, generate_scenario
from vpp_core.scenario_real import generate_scenario_real
from vpp_core.simulator import SimState, validate

logger = logging.getLogger(__name__)

CONTROLLER_NAMES = ("reguli", "mpc")
DATA_SOURCES = ("real", "sintetic")
EPS = 1e-9
MIN_TRADE_KWH = 0.005   # smaller seller->buyer shares are not worth a wallet transaction
HISTORY_SIZE = 600


def data_day(day: date, year: int) -> date:
    """The same month and day in the data year; 29 February maps to 28 February."""
    try:
        return day.replace(year=year)
    except ValueError:
        return day.replace(year=year, day=28)


def real_data_missing(year: int, days: tuple[date, ...] = ()) -> str | None:
    """Why the real data cannot be used for `days` with the prices of `year`, or None."""
    if year not in ds.PRICE_YEARS:
        return f"SIM_PRICE_YEAR={year}, dar exista preturi doar pentru {ds.PRICE_YEARS}"
    missing = [p.name for p in (ds.prices_csv(year), ds.PV_CSV, ds.DEER_CSV) if not p.exists()]
    if missing:
        return f"lipsesc {', '.join(missing)} din {ds.DATA_DIR}"
    last = ds.last_price_day(year)
    if any(data_day(d, year) > last for d in days):
        return f"preturile {year} se termina pe {last:%d.%m.%Y}"
    return None


@dataclass(frozen=True)
class SimConfig:
    controller: str = "reguli"
    tick_seconds: float = 2.0
    import_max_kw: float = 50.0
    export_max_kw: float = 40.0
    internal_line_kw: float = 30.0
    p2p_price_factor: float = 0.7
    min_p2p_balance_lei: float = 5.0
    seed: int = 42

    def check(self) -> None:
        if self.controller not in CONTROLLER_NAMES:
            raise ValueError(f"controller trebuie sa fie unul din {CONTROLLER_NAMES}")
        if not 0.2 <= self.tick_seconds <= 60:
            raise ValueError("tick_seconds trebuie sa fie intre 0.2 si 60")
        for name in ("import_max_kw", "export_max_kw", "internal_line_kw", "min_p2p_balance_lei"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} trebuie sa fie >= 0")
        if not 0 < self.p2p_price_factor <= 1:
            raise ValueError("p2p_price_factor trebuie sa fie in (0, 1]")

    @property
    def grid(self) -> GridParams:
        return GridParams(self.import_max_kw, self.export_max_kw, self.internal_line_kw)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SimConfig:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)

    @classmethod
    def from_settings(cls) -> SimConfig:
        return cls(controller=settings.sim_controller, tick_seconds=settings.sim_tick_seconds, seed=settings.sim_seed)


@dataclass
class StepInputs:
    """What one step starts from, per house (arrays of length H) plus the prices of the step."""
    t: int
    pv_kw: np.ndarray
    load_kw: np.ndarray        # switched-on devices
    price_import: float
    price_export: float
    price_p2p: float


def make_controller(name: str, history_source=None):
    if name == "mpc":
        return RealisticMPCController(name="mpc", history_source=history_source)
    return RuleBasedController(apply_alpha=True, name="reguli")


class Observations:
    """PV and load readings of the simulated steps and the prices they were settled at, per day; the only
    past the MPC forecaster gets in the live loop (NaN where a house has no reading)."""

    def __init__(self, dt_h: float, keep_days: int = HISTORY_DAYS):
        self.dt_h = dt_h
        self.keep_days = keep_days
        self.readings: dict[date, dict[int, np.ndarray]] = {}   # day -> house id -> (2, spd) pv, load kW
        self.prices: dict[date, np.ndarray] = {}                # day -> (3, spd) import, export, p2p

    @property
    def steps_per_day(self) -> int:
        return round(24 / self.dt_h)

    def clear(self) -> None:
        self.readings.clear()
        self.prices.clear()

    def record(self, day: date, t: int, house_ids: list[int], pv_kw, load_kw, prices: tuple[float, ...]) -> None:
        spd = self.steps_per_day
        houses = self.readings.setdefault(day, {})
        for i, house_id in enumerate(house_ids):
            houses.setdefault(house_id, np.full((2, spd), np.nan))[:, t] = (pv_kw[i], load_kw[i])
        self.prices.setdefault(day, np.full((3, spd), np.nan))[:, t] = prices
        oldest = max(self.readings) - timedelta(days=self.keep_days)
        for store in (self.readings, self.prices):
            for old in [d for d in store if d < oldest]:
                del store[old]

    def history(self, day: date, t: int, house_ids: list[int], scenario: Scenario, delay_steps: int = 1) -> History:
        """History of step t of `day`; `scenario` (today and tomorrow) gives only the published prices."""
        spd = self.steps_per_day
        start = day - timedelta(days=self.keep_days)
        now = self.keep_days * spd + t
        readings = np.full((2, len(house_ids), now + spd), np.nan)
        prices = np.full((3, self.keep_days * spd), np.nan)
        for k in range(self.keep_days + 1):
            d = start + timedelta(days=k)
            for i, house_id in enumerate(house_ids):
                if house_id in self.readings.get(d, {}):
                    readings[:, i, k * spd:(k + 1) * spd] = self.readings[d][house_id]
            if k < self.keep_days and d in self.prices:
                prices[:, k * spd:(k + 1) * spd] = self.prices[d]
        n_obs = now + 1 - delay_steps
        n_today = published_steps(start, now, self.dt_h) - self.keep_days * spd
        published = [np.concatenate([prices[j], getattr(scenario, name)[:n_today]])
                     for j, name in enumerate(("price_import", "price_export", "price_p2p"))]
        return History(start=start, dt_h=self.dt_h, now=now, pv_kw=readings[0, :, :n_obs],
                       load_kw=readings[1, :, :n_obs], price_import=published[0], price_export=published[1],
                       price_p2p=published[2])


def community_from_houses(houses: list[HouseModel], grid: GridParams, min_p2p_balance: float) -> CommunityParams:
    params = []
    for h in houses:
        battery = None
        init_ratio = 0.5
        if h.battery:
            b = h.battery
            # a backup reserve raised above the stored energy is reached by charging: until then the floor is
            # the current SOC, otherwise the battery would be clamped up to the reserve with energy from nowhere
            soc_min = min(b.soc_min_kwh, b.soc_kwh)
            battery = BatteryParams(
                capacity_kwh=b.capacity_kwh, soc_min_ratio=min(max(soc_min / b.capacity_kwh, 0.0), 0.95),
                p_ch_max_kw=b.p_ch_max_kw, p_dis_max_kw=b.p_dis_max_kw, eta_ch=b.eta_ch, eta_dis=b.eta_dis,
            )
            init_ratio = max(0.5, battery.soc_min_ratio)
        prefs = h.trading_preferences
        # vpp_core has a single P2P flag per house: a house takes part only if it may both sell and buy
        p2p = bool(prefs and prefs.selling_enabled and prefs.buying_enabled)
        if p2p and h.wallet is not None and h.wallet.balance_lei < min_p2p_balance:
            p2p = False
        params.append(HouseParams(
            id=h.id, pv_kwp=h.pv_capacity_kw if h.has_pv else 0.0, battery=battery,
            mode=h.mode if h.mode in ("Eco", "Profit") else "Eco", p2p_enabled=p2p, initial_soc_ratio=init_ratio,
        ))
    return CommunityParams(houses=tuple(params), grid=grid)


class SimulationLoop:
    def __init__(self):
        if settings.sim_data not in DATA_SOURCES:
            raise ValueError(f"SIM_DATA trebuie sa fie unul din {DATA_SOURCES}")
        self.config = SimConfig.from_settings()
        self.dt_h = settings.sim_dt_hours
        self.data_year = settings.sim_price_year
        self.data_source = "sintetic"
        self.day: date = settings.sim_start_date
        self.t = 0                      # step index inside the current day
        self.total_steps = 0
        self.running = False
        self.paused = False
        self.loaded = False
        self.last_error: str | None = None
        self.community: CommunityParams | None = None
        self.scenario: Scenario | None = None
        self.scenario_key = None
        self.controller = None
        self.batteries: list[Battery | None] = []
        self.house_ids: list[int] = []
        self.profiles = DeviceProfiles(self.dt_h)
        self.device_kw: dict[int, np.ndarray] = {}     # device id -> kW over the scenario window while on
        self.history: deque = deque(maxlen=HISTORY_SIZE)
        self.observations = Observations(self.dt_h)
        self.last_result: dict | None = None
        self.lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._ws_clients: list = []
        self._fallback_reason: str | None = None

    @property
    def steps_per_day(self) -> int:
        return round(24 / self.dt_h)

    @property
    def window_days(self) -> tuple[date, date]:
        return self.day, self.day + timedelta(days=1)

    def _resolve_data_source(self) -> str:
        if settings.sim_data != "real":
            return "sintetic"
        reason = real_data_missing(self.data_year, self.window_days)
        if reason is None:
            self._fallback_reason = None
            return "real"
        if reason != self._fallback_reason:
            logger.warning("Date reale indisponibile (%s): PV si preturi sintetice", reason)
            self._fallback_reason = reason
        return "sintetic"

    @property
    def sim_datetime(self) -> datetime:
        return self._clock_at(self.day, self.t)

    def _clock_at(self, day: date, t: int) -> datetime:
        return datetime.combine(day, datetime.min.time()) + timedelta(hours=t * self.dt_h)

    def _next_clock(self) -> tuple[date, int]:
        if self.t + 1 >= self.steps_per_day:
            return self.day + timedelta(days=1), 0
        return self.day, self.t + 1

    def current_prices(self) -> tuple[float, float, float]:
        """(import, export, p2p) lei/kWh at the current step."""
        sc, t = self.scenario, self.t
        return float(sc.price_import[t]), float(sc.price_export[t]), float(sc.price_p2p[t])

    async def load(self) -> None:
        async with get_session_context() as session:
            state = await session.get(SimulationStateModel, 1)
            if state is not None:
                self._restore_state(state)
            await self._restore_observations(session)
            self._sync(await HouseRepository(session).get_all_with_relations())
        self.loaded = True
        logger.info("Simulation loaded: %d houses, controller %s, sim time %s",
                    len(self.house_ids), self.config.controller, self.sim_datetime.isoformat())

    def _restore_state(self, state: SimulationStateModel) -> None:
        self.total_steps = state.total_steps
        if state.config_json:
            try:
                cfg = SimConfig.from_dict(json.loads(state.config_json))
                cfg.check()
                self.config = cfg
            except (ValueError, TypeError) as e:
                logger.warning("Ignoring saved config: %s", e)
        if state.sim_datetime is not None:
            self.day = state.sim_datetime.date()
            minutes = state.sim_datetime.hour * 60 + state.sim_datetime.minute
            self.t = min(round(minutes / (self.dt_h * 60)), self.steps_per_day - 1)

    async def _restore_observations(self, session: AsyncSession) -> None:
        """The readings of the last days from house_steps, so the MPC keeps its history after a restart."""
        self.observations.clear()
        first = self._clock_at(self.day - timedelta(days=self.observations.keep_days), 0)
        rows = (await session.execute(
            select(HouseStepModel).where(HouseStepModel.sim_timestamp >= first,
                                         HouseStepModel.sim_timestamp < self.sim_datetime)
            .order_by(HouseStepModel.sim_timestamp)
        )).scalars()
        for row in rows:
            ts = row.sim_timestamp
            t = round((ts.hour * 60 + ts.minute) / (self.dt_h * 60))
            if t < self.steps_per_day:
                self.observations.record(ts.date(), t, [row.house_id], [row.pv_kw], [row.load_kw],
                                         (row.price_import, row.price_export, row.price_p2p))

    def _history(self, t: int) -> History:
        return self.observations.history(self.day, t, self.house_ids, self.scenario)

    async def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.paused = False
        self.last_error = None
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        while self.running:
            if not self.paused:
                try:
                    result = await self.step()
                    await self.broadcast(result)
                except Exception as e:
                    logger.exception("Simulation step failed")
                    self.last_error = str(e)
                    self.paused = True
            await asyncio.sleep(self.config.tick_seconds)

    def _sync(self, houses: list[HouseModel]) -> None:
        community = community_from_houses(houses, self.config.grid, self.config.min_p2p_balance_lei)
        ids = [h.id for h in houses]
        self.data_source = self._resolve_data_source()
        key = (self.day, tuple(hp.pv_kwp for hp in community.houses), self.config.p2p_price_factor, self.config.seed,
               self.data_source)
        rebuild_scenario = self.scenario is None or key != self.scenario_key
        rebuild = rebuild_scenario or community != self.community or self.controller is None

        if community != self.community or ids != self.house_ids:
            self.batteries = self._rebuild_batteries(houses, community)
            self.house_ids = ids
            self.community = community
        if rebuild_scenario:
            self.scenario = self._build_scenario(self.day)
            self.scenario_key = key
        if self.controller is None or getattr(self.controller, "name", None) != self.config.controller:
            self.controller = make_controller(self.config.controller, self._history)
            rebuild = True
        if rebuild:
            self.controller.reset(self.community, self.scenario)

    def _rebuild_batteries(self, houses: list[HouseModel], community: CommunityParams) -> list[Battery | None]:
        previous = dict(zip(self.house_ids, self.batteries, strict=True))
        batteries = []
        for h, hp in zip(houses, community.houses, strict=True):
            if hp.battery is None:
                batteries.append(None)
                continue
            prev = previous.get(h.id)
            soc = prev.soc_kwh if prev is not None else h.battery.soc_kwh
            soc = min(max(soc, hp.battery.soc_min_kwh), hp.battery.soc_max_kwh)
            batteries.append(Battery(hp.battery, soc))
        return batteries

    def _build_scenario(self, day: date) -> Scenario:
        """PV and prices for today and tomorrow, each day generated with its own date-based seed and
        concatenated, so the day the MPC looks ahead to is exactly the one simulated tomorrow. The load
        columns start empty: _apply_device_load fills them from the devices before every step."""
        parts = []
        for d in self.window_days:
            seed = self.config.seed + d.toordinal()
            if self.data_source == "real":
                part = generate_scenario_real(self.community, start=data_day(d, ds.YEAR), n_days=1,
                                              dt_h=self.dt_h, seed=seed, p2p_price_factor=self.config.p2p_price_factor,
                                              load_source="deer", price_year=self.data_year)
            else:
                part = generate_scenario(self.community, start=d, n_days=1, dt_h=self.dt_h, seed=seed,
                                         p2p_price_factor=self.config.p2p_price_factor, load_source="sintetic")
            parts.append(part)

        def cat(name: str) -> np.ndarray:
            return np.concatenate([getattr(p, name) for p in parts], axis=-1)

        empty = np.zeros((self.community.n_houses, 2 * self.steps_per_day))
        return Scenario(
            dt_h=self.dt_h, start=day, pv_kw=cat("pv_kw"), load_crit_kw=empty, load_flex_kw=empty.copy(),
            price_import=cat("price_import"), price_export=cat("price_export"), price_p2p=cat("price_p2p"),
            seed=parts[0].seed,
        )

    def _apply_device_load(self, houses: list[HouseModel]) -> None:
        """Scenario load over the window = the switched-on devices as they are now; written in place. The
        controllers read only step t of it (the MPC forecasts the rest from Observations)."""
        days = self.window_days
        self.profiles.keep_days(days)
        sc, kw = self.scenario, {}
        for i, h in enumerate(houses):
            kw.update(self.profiles.device_kw(h, days, self.config.seed))
            sc.load_crit_kw[i], sc.load_flex_kw[i] = house_load(h, kw, sc.n_steps)
        self.device_kw = kw

    async def step(self) -> dict:
        async with self.lock:
            return await self._step()

    async def _step(self) -> dict:
        async with get_session_context() as session:
            houses = await HouseRepository(session).get_all_with_relations()
            if not houses:
                raise RuntimeError("nu exista case in baza de date")
            self._sync(houses)
            self._apply_device_load(houses)
            inputs = self._step_inputs()
            dispatch = await self._dispatch()
            soc_before = [b.soc_kwh if b else None for b in self.batteries]
            try:
                self._apply_to_batteries(dispatch)
                trades = self._split_trades(dispatch, houses, inputs)
                settled = await self._persist(session, houses, inputs, dispatch, trades)
            except Exception:
                for b, soc in zip(self.batteries, soc_before, strict=True):
                    if b is not None:
                        b.soc_kwh = soc
                raise
        self.observations.record(self.day, inputs.t, self.house_ids, inputs.pv_kw, inputs.load_kw,
                                 (inputs.price_import, inputs.price_export, inputs.price_p2p))
        result = self._result(houses, inputs, dispatch, settled)
        day = self.day
        self._advance_clock(result)
        if self.day != day:
            # the new day's prices must be there right after midnight, not only after its first step
            self._sync(houses)
        return result

    def _step_inputs(self) -> StepInputs:
        sc, t = self.scenario, self.t
        p_imp, p_exp, p_p2p = self.current_prices()
        return StepInputs(t=t, pv_kw=sc.pv_kw[:, t].copy(), load_kw=sc.load_kw[:, t].copy(),
                          price_import=p_imp, price_export=p_exp, price_p2p=p_p2p)

    async def _dispatch(self) -> Dispatch:
        state = SimState(t=self.t, batteries=self.batteries)
        dispatch: Dispatch = await asyncio.to_thread(self.controller.dispatch, state)   # MPC solves an LP
        validate(dispatch, self.community, self.scenario, self.t)
        for name in FLOWS:
            setattr(dispatch, name, np.clip(getattr(dispatch, name), 0, None))
        return dispatch

    def _apply_to_batteries(self, dispatch: Dispatch) -> None:
        for i, battery in enumerate(self.batteries):
            if battery is not None:
                battery.apply(dispatch.ch[i], dispatch.dis[i], self.dt_h)

    def _split_trades(self, dispatch: Dispatch, houses: list[HouseModel], inputs: StepInputs) -> list[Trade]:
        """Seller -> buyer trades, pro rata to what each seller sold."""
        sold, bought = dispatch.p2p_out * self.dt_h, dispatch.p2p_in * self.dt_h
        total_sold = float(sold.sum())
        if total_sold <= EPS:
            return []
        trades = []
        for j, bought_j in enumerate(bought):
            if bought_j <= EPS:
                continue
            for i, sold_i in enumerate(sold):
                share = sold_i * bought_j / total_sold
                if i != j and share >= MIN_TRADE_KWH:
                    trades.append(Trade(houses[i].id, houses[j].id, float(share),
                                        inputs.price_p2p, inputs.price_import))
        return trades

    async def _persist(self, session: AsyncSession, houses: list[HouseModel], inputs: StepInputs,
                       d: Dispatch, trades: list[Trade]) -> list[TradeTransactionModel]:
        """All DB writes of the step; the caller's session commits them together."""
        sim_ts, dt = self.sim_datetime, self.dt_h
        for i, h in enumerate(houses):
            battery = self.batteries[i]
            if h.battery is not None and battery is not None:
                h.battery.soc_kwh = battery.soc_kwh
            load = float(inputs.load_kw[i])
            session.add(HouseStepModel(
                house_id=h.id, sim_timestamp=sim_ts, dt_h=dt, controller=self.config.controller,
                pv_kw=float(inputs.pv_kw[i]), load_kw=load, device_kw=load,
                shed_kw=float(d.shed[i]), curtail_kw=float(d.curtail[i]), ch_kw=float(d.ch[i]), dis_kw=float(d.dis[i]),
                imp_kw=float(d.imp[i]), exp_kw=float(d.exp[i]), p2p_in_kw=float(d.p2p_in[i]),
                p2p_out_kw=float(d.p2p_out[i]), soc_kwh=battery.soc_kwh if battery else 0.0,
                price_import=inputs.price_import, price_export=inputs.price_export, price_p2p=inputs.price_p2p,
            ))
            for dev in h.devices:
                power = float(self.device_kw[dev.id][inputs.t]) if dev.status_on else 0.0
                if dev.current_power_kw != power:
                    dev.current_power_kw = power
                energy = power * dt
                if energy > 0:
                    dev.accumulated_energy_kwh = round(dev.accumulated_energy_kwh + energy, 6)
                    session.add(EnergyLogModel(device_id=dev.id, timestamp=sim_ts, energy_kwh=energy,
                                               event_type="step"))
        settled = await SettlementService(session).settle_trades(trades, sim_ts)
        next_day, next_t = self._next_clock()
        await self._save_state(session, total_steps=self.total_steps + 1, sim_datetime=self._clock_at(next_day, next_t))
        return settled

    async def _save_state(self, session: AsyncSession, **fields) -> None:
        state = await session.get(SimulationStateModel, 1)
        if state is None:
            state = SimulationStateModel(id=1, total_steps=self.total_steps, sim_datetime=self.sim_datetime)
            session.add(state)
        state.config_json = json.dumps(self.config.to_dict())
        for name, value in fields.items():
            setattr(state, name, value)
        await session.flush()

    def _result(self, houses: list[HouseModel], inputs: StepInputs, d: Dispatch,
                settled: list[TradeTransactionModel]) -> dict:
        rows = []
        for i, h in enumerate(houses):
            soc = self.batteries[i].soc_kwh if self.batteries[i] else 0.0
            cap = h.battery.capacity_kwh if h.battery else 0.0
            rows.append({
                "id": h.id, "name": h.name, "mode": h.mode, "p2p_enabled": self.community.houses[i].p2p_enabled,
                "pv_kw": round(float(inputs.pv_kw[i]), 3), "load_kw": round(float(inputs.load_kw[i]), 3),
                "device_kw": round(float(inputs.load_kw[i]), 3), "shed_kw": round(float(d.shed[i]), 3),
                "curtail_kw": round(float(d.curtail[i]), 3), "ch_kw": round(float(d.ch[i]), 3),
                "dis_kw": round(float(d.dis[i]), 3), "imp_kw": round(float(d.imp[i]), 3),
                "exp_kw": round(float(d.exp[i]), 3), "p2p_in_kw": round(float(d.p2p_in[i]), 3),
                "p2p_out_kw": round(float(d.p2p_out[i]), 3), "soc_kwh": round(soc, 3),
                "soc_percent": round(100 * soc / cap, 1) if cap else None,
            })
        socs = [b.soc_kwh for b in self.batteries if b]
        caps = [hp.battery.capacity_kwh for hp in self.community.houses if hp.battery]
        return {
            "step": self.total_steps + 1,
            "sim_datetime": self.sim_datetime.isoformat(),
            "dt_h": self.dt_h,
            "controller": self.config.controller,
            "data_source": self.data_source,
            "price": {"import": round(inputs.price_import, 4), "export": round(inputs.price_export, 4),
                      "p2p": round(inputs.price_p2p, 4)},
            "community": {
                "pv_kw": round(float(inputs.pv_kw.sum()), 3), "load_kw": round(float(inputs.load_kw.sum()), 3),
                "device_kw": round(float(inputs.load_kw.sum()), 3), "shed_kw": round(float(d.shed.sum()), 3),
                "curtail_kw": round(float(d.curtail.sum()), 3), "charge_kw": round(float(d.ch.sum()), 3),
                "discharge_kw": round(float(d.dis.sum()), 3), "import_kw": round(float(d.imp.sum()), 3),
                "export_kw": round(float(d.exp.sum()), 3), "p2p_kw": round(float(d.p2p_out.sum()), 3),
                "soc_kwh": round(sum(socs), 3), "soc_percent": round(100 * sum(socs) / sum(caps), 1) if caps else None,
            },
            "houses": rows,
            "trades": [{
                "seller_house_id": tr.seller_house_id, "buyer_house_id": tr.buyer_house_id,
                "energy_kwh": round(tr.energy_kwh, 4), "price_lei_kwh": round(tr.price_lei_kwh, 4),
                "total_value_lei": round(tr.total_value_lei, 4), "status": tr.status,
            } for tr in settled],
        }

    def _advance_clock(self, result: dict) -> None:
        self.total_steps += 1
        self.day, self.t = self._next_clock()
        self.history.append(result)
        self.last_result = result
        self.last_error = None

    async def apply_config(self, cfg: SimConfig) -> None:
        cfg.check()
        async with self.lock:
            self.config = cfg
            async with get_session_context() as session:
                await self._save_state(session)
                houses = await HouseRepository(session).get_all_with_relations()
                if houses:
                    self._sync(houses)

    async def withdraw_from_battery(self, house_id: int, energy_kwh: float) -> tuple[float, float, WalletModel]:
        """Returns (payment_lei, new_soc_kwh, house wallet); ValueError messages are shown to the user."""
        async with self.lock:
            if house_id not in self.house_ids:
                raise ValueError("casa nu exista in simulare")
            battery = self.batteries[self.house_ids.index(house_id)]
            if battery is None:
                raise ValueError("casa nu are baterie")
            available = battery.soc_kwh - battery.params.soc_min_kwh
            if energy_kwh > available + EPS:
                raise ValueError(f"energie insuficienta in baterie: disponibil {available:.2f} kWh")
            async with get_session_context() as session:
                payment, wallet = await SettlementService(session).pay_reserve_contribution(
                    house_id, energy_kwh, self.sim_datetime)
                await session.execute(update(BatteryModel).where(BatteryModel.house_id == house_id)
                                      .values(soc_kwh=battery.soc_kwh - energy_kwh))
            battery.soc_kwh -= energy_kwh
            return payment, battery.soc_kwh, wallet

    async def reset(self) -> None:
        async with self.lock:
            start_ts = datetime.combine(settings.sim_start_date, datetime.min.time())
            async with get_session_context() as session:
                for model in (HouseStepModel, EnergyLogModel, TradeTransactionModel, WalletTransactionModel):
                    await session.execute(delete(model))
                await session.execute(update(DeviceModel).values(accumulated_energy_kwh=0.0, current_power_kw=0.0,
                                                                 last_state_change_ts=None))
                await session.execute(update(VPPReserveModel).values(reserved_kwh=0.0))
                for b in (await session.execute(select(BatteryModel))).scalars():
                    b.soc_kwh = max(0.5 * b.capacity_kwh, b.soc_min_kwh)
                for w in (await session.execute(select(WalletModel))).scalars():
                    amount = settings.operator_wallet_lei if w.house_id is None else settings.initial_wallet_lei
                    w.balance_lei, w.total_earned_lei, w.total_spent_lei, w.transaction_count = amount, 0.0, 0.0, 1
                    session.add(WalletTransactionModel(wallet_id=w.id, transaction_type="initial", amount_lei=amount,
                                                       description="Sold initial", balance_after=amount,
                                                       sim_timestamp=start_ts))
                await self._save_state(session, total_steps=0, sim_datetime=start_ts)
                houses = await HouseRepository(session).get_all_with_relations()
            self.day, self.t, self.total_steps = settings.sim_start_date, 0, 0
            self.history.clear()
            self.observations.clear()
            self.last_result = None
            self.last_error = None
            self.batteries, self.house_ids, self.community, self.scenario = [], [], None, None
            if houses:
                self._sync(houses)

    def status(self) -> dict:
        ts = self.sim_datetime
        return {
            "running": self.running,
            "paused": self.paused,
            "loaded": self.loaded,
            "controller": self.config.controller,
            "data_source": self.data_source,
            "data_year": self.data_year,
            "tick_seconds": self.config.tick_seconds,
            "dt_hours": self.dt_h,
            "total_steps": self.total_steps,
            "sim_datetime": ts.isoformat(),
            "sim_date": ts.date().isoformat(),
            "sim_time": ts.strftime("%H:%M"),
            "step_of_day": self.t,
            "steps_per_day": self.steps_per_day,
            "n_houses": len(self.house_ids),
            "last_error": self.last_error,
            "websocket_clients": len(self._ws_clients),
        }

    def prices_today(self) -> list[dict]:
        if self.scenario is None:
            return []
        sc = self.scenario
        return [{
            "sim_timestamp": self._clock_at(self.day, t).isoformat(),
            "price_import": round(float(sc.price_import[t]), 4),
            "price_export": round(float(sc.price_export[t]), 4),
            "price_p2p": round(float(sc.price_p2p[t]), 4),
        } for t in range(self.steps_per_day)]

    def house_last_step(self, house_id: int) -> dict | None:
        if not self.last_result:
            return None
        return next((h for h in self.last_result["houses"] if h["id"] == house_id), None)

    def add_ws(self, ws) -> None:
        self._ws_clients.append(ws)

    def remove_ws(self, ws) -> None:
        if ws in self._ws_clients:
            self._ws_clients.remove(ws)

    async def broadcast(self, result: dict) -> None:
        if not self._ws_clients:
            return
        message = {"type": "step", "data": result, "status": self.status()}
        for ws in list(self._ws_clients):
            try:
                await ws.send_json(message)
            except Exception:
                self.remove_ws(ws)


sim = SimulationLoop()
