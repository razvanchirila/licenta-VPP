"""Controller interface and the rule-based strategy (LP / MPC are in optimizer.py)."""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from vpp_core.dispatch import Dispatch
from vpp_core.params import CommunityParams
from vpp_core.scenario import Scenario
from vpp_core.simulator import SimState

# share of the flexible load that is kept, per user mode and price zone
ALPHA = {
    "Eco": {"cheap": 1.0, "normal": 0.6, "expensive": 0.3},
    "Profit": {"cheap": 0.8, "normal": 0.4, "expensive": 0.1},
}


class Controller(ABC):
    """reset() once per run, dispatch() once per step."""

    name = "controller"

    def reset(self, community: CommunityParams, scenario: Scenario) -> None:
        self.community = community
        self.scenario = scenario

    @abstractmethod
    def dispatch(self, state: SimState) -> Dispatch: ...


def price_zones(price: np.ndarray, steps_per_day: int, cheap_q: float, expensive_q: float) -> np.ndarray:
    """(n_steps,) labels 'cheap' / 'normal' / 'expensive' from the quantiles of each day (level-independent)."""
    zones = np.full(price.shape, "normal", dtype=object)
    for day_start in range(0, len(price), steps_per_day):
        day = price[day_start : day_start + steps_per_day]
        low, high = np.quantile(day, [cheap_q, expensive_q])
        zones[day_start : day_start + steps_per_day][day <= low] = "cheap"
        zones[day_start : day_start + steps_per_day][day >= high] = "expensive"
    return zones


class RuleBasedController(Controller):
    """Priority rules per step: shed flexible load, own PV, battery, neighbours, grid, arbitrage.
    Every flag switches one rule off, which gives the baseline strategies."""

    def __init__(
        self,
        use_battery: bool = True,
        p2p: bool = True,
        arbitrage: bool = True,
        apply_alpha: bool = True,
        p2p_before_battery: bool = False,
        cheap_quantile: float = 0.25,
        expensive_quantile: float = 0.75,
        arbitrage_target_ratio: float = 0.8,
        name: str = "vpp_reguli",
    ):
        self.use_battery = use_battery
        self.p2p = p2p
        self.arbitrage = arbitrage
        self.apply_alpha = apply_alpha
        self.p2p_before_battery = p2p_before_battery
        self.cheap_quantile = cheap_quantile
        self.expensive_quantile = expensive_quantile
        self.arbitrage_target_ratio = arbitrage_target_ratio
        self.name = name

    def reset(self, community: CommunityParams, scenario: Scenario) -> None:
        super().reset(community, scenario)
        houses = community.houses
        self.zones = price_zones(
            scenario.price_import, scenario.steps_per_day, self.cheap_quantile, self.expensive_quantile
        )
        self.p2p_mask = np.array([house.p2p_enabled for house in houses], dtype=float)
        self.is_profit = np.array([house.mode == "Profit" for house in houses])
        self.has_battery = np.array([house.battery is not None for house in houses])
        self.capacity_kwh = np.array([house.battery.capacity_kwh if house.battery else 0.0 for house in houses])
        self.eta_ch = np.array([house.battery.eta_ch if house.battery else 1.0 for house in houses])

    def _shed_flexible_load(self, dispatch: Dispatch, flex: np.ndarray, t: int) -> None:
        if not self.apply_alpha:
            return
        zone = self.zones[t]
        alpha = np.array([ALPHA[house.mode][zone] for house in self.community.houses])
        dispatch.shed = (1 - alpha) * flex

    def _use_battery(
        self, dispatch: Dispatch, surplus: np.ndarray, deficit: np.ndarray,
        max_charge: np.ndarray, max_discharge: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        dispatch.dis = np.minimum(deficit, max_discharge)
        deficit = deficit - dispatch.dis
        dispatch.ch = np.minimum(surplus, max_charge)
        surplus = surplus - dispatch.ch
        return surplus, deficit

    def _trade_p2p(
        self, dispatch: Dispatch, surplus: np.ndarray, deficit: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        if not self.p2p:
            return surplus, deficit
        offered = surplus * self.p2p_mask
        wanted = deficit * self.p2p_mask
        traded = min(offered.sum(), wanted.sum(), self.community.grid.internal_line_kw)
        if traded <= 0:
            return surplus, deficit
        dispatch.p2p_out = offered * (traded / offered.sum())
        dispatch.p2p_in = wanted * (traded / wanted.sum())
        return surplus - dispatch.p2p_out, deficit - dispatch.p2p_in

    def _export_or_curtail(self, dispatch: Dispatch, surplus: np.ndarray) -> None:
        grid = self.community.grid
        dispatch.exp = surplus.copy()
        if dispatch.exp.sum() > grid.export_max_kw:
            dispatch.exp *= grid.export_max_kw / dispatch.exp.sum()
        dispatch.curtail = surplus - dispatch.exp

    def _import_or_shed(self, dispatch: Dispatch, deficit: np.ndarray) -> None:
        grid = self.community.grid
        dispatch.imp = deficit.copy()
        if dispatch.imp.sum() > grid.import_max_kw:
            dispatch.imp *= grid.import_max_kw / dispatch.imp.sum()
            dispatch.shed = dispatch.shed + (deficit - dispatch.imp)

    def _arbitrage(self, dispatch: Dispatch, state: SimState, max_charge: np.ndarray, dt_h: float) -> None:
        if not (self.arbitrage and self.use_battery and self.zones[state.t] == "cheap"):
            return
        candidates = self.is_profit & self.has_battery & (dispatch.dis <= 0)
        target_kw = (self.arbitrage_target_ratio * self.capacity_kwh - state.soc_kwh) / (self.eta_ch * dt_h)
        wanted = np.where(candidates, np.clip(np.minimum(max_charge - dispatch.ch, target_kw), 0, None), 0.0)
        headroom = max(self.community.grid.import_max_kw - dispatch.imp.sum(), 0.0)
        if wanted.sum() > headroom:
            wanted *= headroom / wanted.sum()
        dispatch.ch = dispatch.ch + wanted
        dispatch.imp = dispatch.imp + wanted

    def dispatch(self, state: SimState) -> Dispatch:
        scenario, t, dt_h = self.scenario, state.t, self.scenario.dt_h
        n_houses = self.community.n_houses
        pv = scenario.pv_kw[:, t]
        critical, flex = scenario.load_crit_kw[:, t], scenario.load_flex_kw[:, t]
        dispatch = Dispatch.zeros(n_houses)

        self._shed_flexible_load(dispatch, flex, t)
        load = critical + flex - dispatch.shed

        direct = np.minimum(pv, load)
        surplus = pv - direct
        deficit = load - direct

        zeros = np.zeros(n_houses)
        max_charge = state.max_charge_kw(dt_h) if self.use_battery else zeros
        max_discharge = state.max_discharge_kw(dt_h) if self.use_battery else zeros

        if self.p2p_before_battery:
            surplus, deficit = self._trade_p2p(dispatch, surplus, deficit)
            surplus, deficit = self._use_battery(dispatch, surplus, deficit, max_charge, max_discharge)
        else:
            surplus, deficit = self._use_battery(dispatch, surplus, deficit, max_charge, max_discharge)
            surplus, deficit = self._trade_p2p(dispatch, surplus, deficit)

        self._export_or_curtail(dispatch, surplus)
        self._import_or_shed(dispatch, deficit)
        self._arbitrage(dispatch, state, max_charge, dt_h)
        return dispatch
