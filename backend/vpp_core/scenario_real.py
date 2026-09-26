"""
Scenario from real 2023 data (PVGIS, PZU via data_sources.py); sources in backend/data/README.md.
Load: the appliance list (load_source="dispozitive", backend/data/dispozitive.csv, see load_model.py) or the
DEER statistical profile scaled to an annual consumption ("deer").

    import  = (PZU + SUPPLY_MARGIN + NETWORK_ADDER) x (1 + VAT)
              PZU: Ember/ENTSO-E day-ahead, lei/kWh at 4.9465 RON/EUR
              SUPPLY_MARGIN 0.223: Hidroelectrica Hidro DINAMIC C, Jan 2025 (0.15 + 0.073 lei/kWh)
              NETWORK_ADDER 0.5345: regulated, excl. VAT (Electrica Furnizare, Delgaz Grid area, 2026):
              transport 0.03645 + system services 0.01470 + distribution LV 0.38791 + green
              certificates 0.07402 + cogeneration 0.01360 + excise 0.00768 + CfD 0.00014
    export  = PZU + SUPPLY_MARGIN  (export_rule="energie_activa": ANRE, prosumers <= 200 kW are paid
              the contract's active energy price); export_rule="pzu" gives PZU only (> 200 kW / post-2030)
    p2p     = p2p_price_factor x import
"""
from __future__ import annotations

from datetime import date, timedelta

import numpy as np

from vpp_core import data_sources as ds
from vpp_core.params import CommunityParams
from vpp_core.scenario import Scenario, _season, steps_per_day_of

SUPPLY_MARGIN = 0.223       # lei/kWh, excl. VAT
NETWORK_ADDER = 0.5345      # lei/kWh, excl. VAT
VAT = 0.21

EXPORT_RULES = ("energie_activa", "pzu")
LOAD_SOURCES = ("dispozitive", "deer")


def resample_hourly(hourly: np.ndarray, dt_h: float) -> np.ndarray:
    """(D, 24) hourly averages -> (D * 24 / dt_h,) step averages; interpolated, then rescaled so
    each hour keeps its energy."""
    flat = np.asarray(hourly, dtype=float).ravel()
    steps_per_hour = 1 / dt_h
    if abs(steps_per_hour - round(steps_per_hour)) < 1e-9 and round(steps_per_hour) >= 1:
        k = int(round(steps_per_hour))
        if k == 1:
            return flat.copy()
        n_hours = len(flat)
        hour_midpoints = np.arange(n_hours) + 0.5
        step_midpoints = (np.arange(n_hours * k) + 0.5) / k
        steps = np.interp(step_midpoints, hour_midpoints, flat).reshape(n_hours, k)
        steps = np.clip(steps, 0, None)
        hour_mean = steps.mean(axis=1, keepdims=True)
        steps = np.where(hour_mean > 1e-12, steps * (flat[:, None] / np.where(hour_mean > 1e-12, hour_mean, 1.0)), 0.0)
        return steps.ravel()
    hours_per_step = dt_h
    if abs(hours_per_step - round(hours_per_step)) < 1e-9 and 24 % int(round(hours_per_step)) == 0:
        return flat.reshape(-1, int(round(hours_per_step))).mean(axis=1)
    raise ValueError("dt_h must be 1/k hours or a whole number of hours dividing 24")


def repeat_hourly(hourly: np.ndarray, dt_h: float) -> np.ndarray:
    """(D, 24) hourly values -> per step, step-hold (block mean for dt_h > 1 h)."""
    flat = np.asarray(hourly, dtype=float).ravel()
    steps_per_hour = 1 / dt_h
    if abs(steps_per_hour - round(steps_per_hour)) < 1e-9:
        return np.repeat(flat, int(round(steps_per_hour)))
    return flat.reshape(-1, int(round(dt_h))).mean(axis=1)


def _deer_profile(weights96: np.ndarray, dt_h: float) -> np.ndarray:
    """96 quarter-hour weights -> weights per step (sum 1)."""
    spd = round(24 / dt_h)
    if spd == 96:
        return weights96.copy()
    if spd < 96 and 96 % spd == 0:
        return weights96.reshape(spd, -1).sum(axis=1)
    if spd > 96 and spd % 96 == 0:
        ratio = spd // 96
        return np.repeat(weights96 / ratio, ratio)
    raise ValueError("dt_h must divide or be a multiple of 15 min")


def _check_dates(start: date, n_days: int) -> None:
    end = start + timedelta(days=n_days - 1)
    if start.year != ds.YEAR or end.year != ds.YEAR:
        raise ValueError(f"datele reale acopera doar {ds.YEAR}: {start} + {n_days} zile iese din an")


def _pv_from_pvgis(
    community: CommunityParams, first_day: int, n_days: int, dt_h: float, spd: int, rng: np.random.Generator
) -> np.ndarray:
    """(n_houses, n_steps) kW: PVGIS kW/kWp x kWp x per-house scale (orientation), shifted +-1 step."""
    n_houses = community.n_houses
    unit_kw = resample_hourly(ds.load_pv_kw_per_kwp()[first_day : first_day + n_days], dt_h)   # (n_steps,)
    kwp = np.array([house.pv_kwp for house in community.houses])
    scale = rng.uniform(0.92, 1.05, n_houses)
    shift = rng.integers(-1, 2, n_houses) if spd >= 48 else np.zeros(n_houses, dtype=int)
    pv = np.empty((n_houses, n_days * spd))
    for h in range(n_houses):
        pv[h] = kwp[h] * scale[h] * np.roll(unit_kw, int(shift[h]))
    return np.clip(pv, 0, None)


def _load_from_deer(
    n_houses: int, days: list[date], dt_h: float, spd: int, season: np.ndarray,
    annual_kwh_lo: float, annual_kwh_hi: float, rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible), each (n_houses, n_steps) kW: DEER profile of the day type with noise,
    scaled so every day's energy equals its target exactly."""
    n_days, n_steps = len(days), len(days) * spd
    weights96 = ds.load_deer_weights()
    profiles = [_deer_profile(weights96[:, ds.deer_day_type(day)], dt_h) for day in days]
    annual_kwh = rng.uniform(annual_kwh_lo, annual_kwh_hi, n_houses)
    daily_target = annual_kwh[:, None] / 365 * (1 - 0.15 * season[None, ::spd])          # (n_houses, n_days) kWh
    critical = np.repeat(rng.uniform(0.10, 0.22, n_houses)[:, None], n_steps, axis=1)
    flex_target = np.clip(daily_target - critical[:, 0:1] * 24, 0.5, None)              # kWh per day
    flexible = np.empty((n_houses, n_steps))
    cycle_steps = max(1, round(1.5 / dt_h))
    for h in range(n_houses):
        for d in range(n_days):
            day_start = d * spd
            shape = profiles[d] * rng.lognormal(0, 0.3, spd)
            if rng.random() < 0.5:
                cycle_start = rng.integers(round(9 / dt_h), round(21 / dt_h))
                shape[cycle_start : cycle_start + cycle_steps] += 2.0 * dt_h / flex_target[h, d]   # 2 kW as a weight
            shape = shape / shape.sum()
            flexible[h, day_start : day_start + spd] = flex_target[h, d] * shape / dt_h  # kW per step
    return critical, flexible


def _prices_from_pzu(
    first_day: int, n_days: int, dt_h: float, p2p_price_factor: float, export_rule: str
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(import, export, p2p), each (n_steps,) lei/kWh (formulas in the module docstring)."""
    pzu = repeat_hourly(ds.load_prices_lei_kwh()[first_day : first_day + n_days], dt_h)
    price_import = (pzu + SUPPLY_MARGIN + NETWORK_ADDER) * (1 + VAT)
    price_export = pzu + SUPPLY_MARGIN if export_rule == "energie_activa" else pzu.copy()
    price_p2p = p2p_price_factor * price_import
    return price_import, price_export, price_p2p


def generate_scenario_real(
    community: CommunityParams,
    start: date = date(2023, 6, 1),
    n_days: int = 7,
    dt_h: float = 0.25,
    seed: int = 0,
    annual_kwh_lo: float = 3000.0,
    annual_kwh_hi: float = 4500.0,
    p2p_price_factor: float = 0.7,
    export_rule: str = "energie_activa",
    load_source: str = "dispozitive",
) -> Scenario:
    spd = steps_per_day_of(dt_h)
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    if export_rule not in EXPORT_RULES:
        raise ValueError(f"export_rule must be one of {EXPORT_RULES}")
    if load_source not in LOAD_SOURCES:
        raise ValueError(f"load_source must be one of {LOAD_SOURCES}")
    _check_dates(start, n_days)
    rng = np.random.default_rng(seed)
    days = [start + timedelta(days=d) for d in range(n_days)]
    first_day = start.timetuple().tm_yday - 1                       # row index into the (365, 24) arrays
    doy = np.repeat(np.array([day.timetuple().tm_yday for day in days]), spd)
    season = _season(doy)

    pv = _pv_from_pvgis(community, first_day, n_days, dt_h, spd, rng)
    critical, flexible = _load_from_deer(
        community.n_houses, days, dt_h, spd, season, annual_kwh_lo, annual_kwh_hi, rng
    )
    if load_source == "dispozitive":
        from vpp_core.load_model import DISPOZITIVE_CSV, community_load  # here, so `-m vpp_core.load_model` runs clean

        critical, flexible = community_load(community, DISPOZITIVE_CSV, start, n_days, dt_h, seed,
                                            fallback=(critical, flexible))
    price_import, price_export, price_p2p = _prices_from_pzu(first_day, n_days, dt_h, p2p_price_factor, export_rule)

    return Scenario(
        dt_h=dt_h,
        start=start,
        pv_kw=pv,
        load_crit_kw=critical,
        load_flex_kw=flexible,
        price_import=price_import,
        price_export=price_export,
        price_p2p=price_p2p,
        seed=seed,
    )
