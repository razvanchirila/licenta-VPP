"""
Forecasts for the MPC made only from what an operator knows when it decides step `now`: the meter readings
of the steps before it and the day-ahead prices already published. The forecasters get a History (copies
of the past, cut at the decision time by observe()), never the scenario.

    load    per house and slot: mean of the last n_days whole days of the same type (working day, or
            weekend / holiday of the DEER calendar in data_sources); any type when there is none yet; with
            no whole day at all, the DEER profile of the day type x the expected daily energy of the
            house's appliances (load_model)
    pv      per house: the latest whole day as a clear-sky index, r(s) = pv(s) / cs(s), so the forecast for
            slot s of day D is r(s) x cs(D, s), cs = scenario.pv_clear_sky_per_kwp shifted to the solar noon
            seen in the readings; for the rest of today x (csi_today + d) / (csi_ref + d) over the last
            window_h of readings, d = 0.05; capped at 1.1 x the clear-sky output of the panels
    prices  published ones as they are (day D+1 is known from PUBLICATION_HOUR on day D, SDAC / PZU);
            a slot not published yet takes the same slot 7 days earlier, else the latest earlier day
            published. Import, export and P2P prices are affine in PZU with the same coefficients every
            day, so this is the same as forecasting PZU and applying the tariff formula.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import numpy as np

from vpp_core import data_sources as ds
from vpp_core.params import CommunityParams
from vpp_core.scenario import Scenario, pv_clear_sky_per_kwp, steps_per_day_of

HISTORY_DAYS = 7             # meter history before a simulated week (scenario.past); real data: at most 9 in January
PUBLICATION_HOUR = 13.0      # local time; SDAC / PZU closes at 12:00 CET (13:00 in Romania), results follow
LATITUDE_DEG = 46.5
DEFAULT_DAILY_KWH = 11.0     # prior before reset() gives the expected energy of each house's appliances
CLIMATE_CSI = 0.5            # clear-sky index before the first whole day of PV readings
PRICE_LAGS_DAYS = (7, 1, 2, 3, 4, 5, 6)
PARTS = ("pv", "load", "price")


def day_type(day: date) -> int:
    """0 = working day, 1 = weekend or public holiday (deer_day_type without the season)."""
    return ds.deer_day_type(day) % 2


def published_steps(start: date, now: int, dt_h: float) -> int:
    """Steps counted from `start` whose price is known at the start of step `now`: up to the end of the day,
    or of the next day from PUBLICATION_HOUR on."""
    day, slot = divmod(now, steps_per_day_of(dt_h))
    return (day + (2 if slot * dt_h >= PUBLICATION_HOUR - 1e-9 else 1)) * steps_per_day_of(dt_h)


@dataclass(frozen=True)
class History:
    """What is known when step `now` (counted from `start`, a midnight) is decided: PV and load readings of
    steps [0, n_obs) with n_obs <= now + 1 (NaN = no reading), the prices published so far."""

    start: date
    dt_h: float
    now: int
    pv_kw: np.ndarray            # (n_houses, n_obs)
    load_kw: np.ndarray          # (n_houses, n_obs)
    price_import: np.ndarray     # (n_pub,), now < n_pub <= published_steps(start, now, dt_h)
    price_export: np.ndarray
    price_p2p: np.ndarray

    def __post_init__(self) -> None:
        if self.load_kw.shape != self.pv_kw.shape:
            raise ValueError("pv_kw and load_kw must have the same shape")
        if self.n_obs > self.now + 1:
            raise ValueError("readings after the decision step")
        n_pub = len(self.price_import)
        if len(self.price_export) != n_pub or len(self.price_p2p) != n_pub:
            raise ValueError("price series of different lengths")
        if not self.now < n_pub <= published_steps(self.start, self.now, self.dt_h):
            raise ValueError("prices must cover step now and nothing that is not published yet")

    @property
    def n_houses(self) -> int:
        return self.pv_kw.shape[0]

    @property
    def n_obs(self) -> int:
        return self.pv_kw.shape[1]

    @property
    def spd(self) -> int:
        return steps_per_day_of(self.dt_h)

    def day(self, index: int) -> date:
        return self.start + timedelta(days=index)

    def whole_days(self, series: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """(n_houses, D, spd) readings of the days before the day of `now`, and the (n_houses, D) mask of
        the days a house has every reading of."""
        n_days = min(self.n_obs, self.now - self.now % self.spd) // self.spd
        days = series[:, : n_days * self.spd].reshape(self.n_houses, n_days, self.spd)
        return days, np.isfinite(days).all(axis=2)


def observe(scenario: Scenario, t: int, delay_steps: int = 1, day_ahead: bool = True,
            use_past: bool = True) -> History:
    """History at step t of `scenario`: readings up to step t - delay_steps (scenario.past in front), the
    prices published by then (only the current one without day_ahead). Slices are copied, so later
    changes to the scenario cannot reach a forecaster."""
    if delay_steps < 0:
        raise ValueError("delay_steps must be >= 0")
    past = scenario.past if use_past else None
    n_past = 0 if past is None else past.n_steps
    now = n_past + t
    start = scenario.start if past is None else past.start

    def head(name: str, n: int) -> np.ndarray:
        parts = [] if past is None else [getattr(past, name)[..., :n]]
        parts.append(getattr(scenario, name)[..., : max(0, n - n_past)])
        return np.concatenate(parts, axis=-1)

    n_obs = max(0, now + 1 - delay_steps)
    n_pub = min(published_steps(start, now, scenario.dt_h) if day_ahead else now + 1, n_past + scenario.n_steps)
    return History(
        start=start, dt_h=scenario.dt_h, now=now, pv_kw=head("pv_kw", n_obs),
        load_kw=head("load_crit_kw", n_obs) + head("load_flex_kw", n_obs),
        price_import=head("price_import", n_pub), price_export=head("price_export", n_pub),
        price_p2p=head("price_p2p", n_pub),
    )


@dataclass
class Forecast:
    pv_kw: np.ndarray            # (n_houses, n)
    load_kw: np.ndarray          # (n_houses, n)
    price_import: np.ndarray     # (n,)
    price_export: np.ndarray
    price_p2p: np.ndarray


def _last(mask: np.ndarray, n: int) -> np.ndarray:
    """The last n True entries of each row of a (rows, D) mask."""
    from_end = np.cumsum(mask[:, ::-1], axis=1)[:, ::-1]
    return mask & (from_end <= n)


def _target_days(history: History, n: int) -> list[tuple[int, np.ndarray, np.ndarray]]:
    """(day index, forecast columns, slots) for each day the steps [now, now + n) fall on."""
    steps = history.now + np.arange(n)
    days = steps // history.spd
    return [(int(k), np.flatnonzero(days == k), steps[days == k] % history.spd) for k in np.unique(days)]


def appliance_daily_kwh(community: CommunityParams) -> dict[str, np.ndarray]:
    """season -> (n_houses,) expected kWh per day from each house's appliances (load_model.compose_house)."""
    from vpp_core import load_model as lm

    houses = lm.compose_houses(house.id for house in community.houses)
    return {season: np.array([house.kwh_per_day(season) for house in houses]) for season in lm.SEASONS}


class LoadForecaster:
    def __init__(self, n_days: int = 7):
        if n_days < 1:
            raise ValueError("n_days must be >= 1")
        self.n_days = n_days
        self.daily_kwh: dict[str, np.ndarray] | None = None

    def reset(self, community: CommunityParams) -> None:
        self.daily_kwh = appliance_daily_kwh(community)

    def prior(self, day: date, n_houses: int, dt_h: float) -> np.ndarray:
        """(n_houses, spd) kW: DEER profile of the day type scaled to the appliances' daily energy."""
        from vpp_core.load_model import season_of
        from vpp_core.scenario_real import _deer_profile

        weights = _deer_profile(ds.load_deer_weights()[:, ds.deer_day_type(day)], dt_h)
        kwh = np.full(n_houses, DEFAULT_DAILY_KWH) if self.daily_kwh is None else self.daily_kwh[season_of(day)]
        return kwh[:, None] * weights[None, :] / dt_h

    def predict(self, history: History, n: int) -> np.ndarray:
        days, valid = history.whole_days(history.load_kw)
        readings = np.nan_to_num(days)
        types = np.array([day_type(history.day(d)) for d in range(days.shape[1])], dtype=int)
        out = np.empty((history.n_houses, n))
        for k, columns, slots in _target_days(history, n):
            target = history.day(k)
            chosen = _last(valid & (types == day_type(target))[None, :], self.n_days)
            none = ~chosen.any(axis=1)
            chosen[none] = _last(valid, self.n_days)[none]
            counts = chosen.sum(axis=1)
            profile = np.einsum("hd,hds->hs", chosen, readings) / np.maximum(counts, 1)[:, None]
            cold = counts == 0
            if cold.any():
                profile[cold] = self.prior(target, history.n_houses, history.dt_h)[cold]
            out[:, columns] = profile[:, slots]
        return out


class PVForecaster:
    def __init__(self, window_h: float = 2.0, latitude_deg: float = LATITUDE_DEG, regularisation: float = 0.05):
        self.window_h = window_h
        self.latitude_deg = latitude_deg
        self.regularisation = regularisation
        self.kwp: np.ndarray | None = None

    def reset(self, community: CommunityParams) -> None:
        self.kwp = np.array([house.pv_kwp for house in community.houses])

    def _noon_shift_h(self, history: History) -> float:
        """Local hour of the PV centroid over the whole days read - 12: the clock time of solar noon (DST,
        longitude)."""
        days, _ = history.whole_days(history.pv_kw)
        weights = np.nansum(days, axis=(0, 1))
        if weights.sum() <= 1e-9:
            return 0.0
        hours = (np.arange(history.spd) + 0.5) * history.dt_h
        return float(np.clip((weights * hours).sum() / weights.sum() - 12.0, -2.0, 2.0))

    def clear_sky(self, history: History, n_days: int) -> np.ndarray:
        """(n_days, spd) kW per kWp of the clear-sky model on the days from history.start."""
        spd, dt_h = history.spd, history.dt_h
        hours = (np.arange(spd) + 0.5) * dt_h - self._noon_shift_h(history)
        doy = np.array([history.day(d).timetuple().tm_yday for d in range(n_days)])
        return pv_clear_sky_per_kwp(hours[None, :], doy[:, None], self.latitude_deg)

    def predict(self, history: History, n: int) -> np.ndarray:
        spd, n_houses = history.spd, history.n_houses
        kwp = np.ones(n_houses) if self.kwp is None else self.kwp
        today = history.now // spd
        cs = self.clear_sky(history, (history.now + n - 1) // spd + 1)
        days, valid = history.whole_days(history.pv_kw)
        n_days = days.shape[1]

        # kW per unit of clear-sky output: the most a house has delivered near midday, at least its kWp
        midday = cs[:n_days] >= 0.5 * cs[:n_days].max(axis=1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            ratios = np.where(midday[None] & valid[:, :, None], days / cs[None, :n_days], np.nan)
        empirical = np.nan_to_num(ratios, nan=0.0).reshape(n_houses, -1).max(axis=1, initial=0.0)
        capacity = np.maximum(empirical, kwp)

        # reference: each house's latest whole day as clear-sky index; 0.5 before the first one
        has_ref = valid.any(axis=1)
        ref_index = n_days - 1 - np.argmax(valid[:, ::-1], axis=1) if n_days else np.zeros(n_houses, dtype=int)
        reference = np.empty((n_houses, spd))
        for h in range(n_houses):
            if not has_ref[h]:
                reference[h] = CLIMATE_CSI * capacity[h]
                continue
            d = ref_index[h]
            day_cs = cs[d]
            lit = day_cs > 0.02 * day_cs.max()
            mean_ratio = days[h, d, lit].sum() / day_cs[lit].sum()
            reference[h] = np.where(lit, days[h, d] / np.where(lit, day_cs, 1.0), mean_ratio)

        # today's readings of the last window_h against what the reference says for them
        adjust = np.ones(n_houses)
        window_start = max(today * spd, history.n_obs - round(self.window_h / history.dt_h))
        if window_start < history.n_obs:
            slots = np.arange(window_start, history.n_obs) % spd
            cs_window = cs[today, slots]
            if cs_window.max() > 0.1 * cs[today].max():
                observed = history.pv_kw[:, window_start: history.n_obs]
                expected = reference[:, slots] * cs_window
                floor = self.regularisation * capacity * cs_window.sum()
                ratio = (observed.sum(axis=1) + floor) / (expected.sum(axis=1) + floor)
                adjust = np.where(np.isfinite(ratio), ratio, 1.0)

        out = np.empty((n_houses, n))
        for k, columns, slots in _target_days(history, n):
            factor = adjust[:, None] if k == today else 1.0
            out[:, columns] = np.minimum(reference[:, slots] * factor, 1.1 * capacity[:, None]) * cs[k, slots]
        return np.clip(out, 0, None)


class PriceForecaster:
    def __init__(self, lags_days: tuple[int, ...] = PRICE_LAGS_DAYS):
        self.lags_days = lags_days

    def predict_series(self, history: History, series: np.ndarray, n: int) -> np.ndarray:
        steps = history.now + np.arange(n)
        n_pub = len(series)
        out = np.full(n, np.nan)
        known = steps < n_pub
        out[known] = series[steps[known]]
        for lag in self.lags_days:
            source = steps - lag * history.spd
            fill = np.isnan(out) & (source >= 0) & (source < n_pub)
            out[fill] = series[source[fill]]
        if np.isnan(out).any():
            out[np.isnan(out)] = series[np.isfinite(series)][-1]
        return out

    def predict(self, history: History, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return tuple(self.predict_series(history, getattr(history, name), n)
                     for name in ("price_import", "price_export", "price_p2p"))


@dataclass
class RealisticForecaster:
    """The three forecasters plus what the operator sees: delay_steps = readings missing at the decision
    (1: the step being decided is not measured yet), day_ahead = published prices are used, use_past =
    the scenario's meter history before the window is used. `perfect` swaps parts for the true values;
    it exists only for the forecast-error study and is applied by the MPC, which has the scenario."""

    load: LoadForecaster = field(default_factory=LoadForecaster)
    pv: PVForecaster = field(default_factory=PVForecaster)
    price: PriceForecaster = field(default_factory=PriceForecaster)
    delay_steps: int = 1
    day_ahead: bool = True
    use_past: bool = True
    perfect: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not set(self.perfect) <= set(PARTS):
            raise ValueError(f"perfect must be a subset of {PARTS}")

    def reset(self, community: CommunityParams) -> None:
        self.load.reset(community)
        self.pv.reset(community)

    def observe(self, scenario: Scenario, t: int) -> History:
        return observe(scenario, t, self.delay_steps, self.day_ahead, self.use_past)

    def predict(self, history: History, n: int) -> Forecast:
        pv, load = self.pv.predict(history, n), self.load.predict(history, n)
        if history.n_obs > history.now:          # delay 0: the step being decided is measured
            pv[:, 0], load[:, 0] = history.pv_kw[:, history.now], history.load_kw[:, history.now]
        return Forecast(pv, load, *self.price.predict(history, n))
