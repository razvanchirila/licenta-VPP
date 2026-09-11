"""
Input time series for a simulation: PV availability, household load and prices.

Everything is generated from a seeded RNG, so the same (community, start, n_days, dt, seed)
always gives the same scenario. Values are step averages (kW) over steps of dt_h hours.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

import numpy as np

from vpp_core.params import CommunityParams

Weather = Literal["random", "clear", "cloudy"]

PERFORMANCE_RATIO = 0.80   # inverter, temperature, soiling, wiring losses
RETAIL_ADDER = 0.62        # lei/kWh: network tariffs, taxes, supplier margin on top of PZU


@dataclass(frozen=True)
class Scenario:
    dt_h: float
    start: date
    pv_kw: np.ndarray          # (H, T) available PV power per house
    load_crit_kw: np.ndarray   # (H, T) critical load, never shed voluntarily
    load_flex_kw: np.ndarray   # (H, T) non-critical load
    price_import: np.ndarray   # (T,) lei/kWh paid for grid import
    price_export: np.ndarray   # (T,) lei/kWh received for grid export
    price_p2p: np.ndarray      # (T,) lei/kWh internal community price
    seed: int | None = None

    def __post_init__(self):
        H, T = self.pv_kw.shape
        for name in ("load_crit_kw", "load_flex_kw"):
            if getattr(self, name).shape != (H, T):
                raise ValueError(f"{name} must have shape {(H, T)}")
        for name in ("price_import", "price_export", "price_p2p"):
            if getattr(self, name).shape != (T,):
                raise ValueError(f"{name} must have shape {(T,)}")
        for name in ("pv_kw", "load_crit_kw", "load_flex_kw"):
            if (getattr(self, name) < 0).any():
                raise ValueError(f"{name} must be non-negative")
        if self.dt_h <= 0:
            raise ValueError("dt_h must be > 0")

    @property
    def n_houses(self) -> int:
        return self.pv_kw.shape[0]

    @property
    def n_steps(self) -> int:
        return self.pv_kw.shape[1]

    @property
    def steps_per_day(self) -> int:
        return round(24 / self.dt_h)

    @property
    def load_kw(self) -> np.ndarray:
        return self.load_crit_kw + self.load_flex_kw


def _gauss(h: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    return np.exp(-((h - mu) ** 2) / (2 * sigma**2))


def _season(doy: np.ndarray) -> np.ndarray:
    """+1 at the summer solstice, -1 at the winter solstice."""
    return np.cos(2 * np.pi * (doy - 172) / 365)


def pv_clear_sky_per_kwp(hours: np.ndarray, doy: np.ndarray, latitude_deg: float) -> np.ndarray:
    """AC output per kWp under clear sky, from solar elevation (solar time).

    Tilted south-facing modules gain more over horizontal irradiance in winter (low sun)
    than in summer: ~1.55x in December, ~1.05x in June.
    """
    decl = np.radians(23.45) * np.sin(2 * np.pi * (284 + doy) / 365)
    lat = np.radians(latitude_deg)
    omega = np.radians(15 * (hours - 12))
    sin_el = np.sin(lat) * np.sin(decl) + np.cos(lat) * np.cos(decl) * np.cos(omega)
    sin_el = np.clip(sin_el, 0, None)
    tilt_gain = 1.30 - 0.25 * _season(doy)
    return PERFORMANCE_RATIO * tilt_gain * sin_el**1.15


def generate_scenario(
    community: CommunityParams,
    start: date = date(2025, 6, 1),
    n_days: int = 7,
    dt_h: float = 0.25,
    seed: int = 0,
    latitude_deg: float = 46.5,
    weather: Weather = "random",
    p2p_price_factor: float = 0.7,
) -> Scenario:
    spd = round(24 / dt_h)
    if abs(spd * dt_h - 24) > 1e-9:
        raise ValueError("24 h must be a whole number of steps")
    rng = np.random.default_rng(seed)
    H, T = community.n_houses, n_days * spd

    hours = (np.arange(T) % spd + 0.5) * dt_h  # step midpoints
    day_doy = np.array([(start + timedelta(days=d)).timetuple().tm_yday for d in range(n_days)])
    doy = np.repeat(day_doy, spd)
    season = _season(doy)

    # --- PV: clear sky x daily clearness x intra-day cloud noise (same sky for the whole street)
    if weather == "clear":
        sky = np.ones(T)
    elif weather == "cloudy":
        sky = np.full(T, 0.3)
    else:
        mean_k = 0.62 + 0.12 * _season(day_doy)
        k = rng.beta(mean_k * 6, (1 - mean_k) * 6)
        day_factor = np.clip(k, 0.05, 1.0)
        sky = np.repeat(day_factor, spd)
        noise = np.zeros(T)
        for t in range(1, T):
            noise[t] = 0.8 * noise[t - 1] + rng.normal(0, 0.12)
        sky = np.clip(sky * np.exp(noise * (1.2 - sky)), 0.02, 1.0)
    unit = pv_clear_sky_per_kwp(hours, doy, latitude_deg) * sky
    kwp = np.array([h.pv_kwp for h in community.houses])
    orientation = rng.uniform(0.92, 1.05, H)
    pv = np.outer(kwp * orientation, unit)

    # --- Load: base critical load + shaped flexible load + occasional appliance cycles
    shape = 0.35 + 0.8 * _gauss(hours, 7.5, 1.2) + 0.5 * _gauss(hours, 13, 2.0) + 1.3 * _gauss(hours, 20, 2.0)
    crit = np.repeat(rng.uniform(0.10, 0.22, H)[:, None], T, axis=1)
    daily_kwh = rng.uniform(6.0, 11.0, H)[:, None] * (1 - 0.15 * season)[None, :]
    day_shape_kwh = shape[:spd].sum() * dt_h
    flex_kwh = np.clip(daily_kwh - crit * 24, 0.5, None)
    flex = flex_kwh * shape[None, :] / day_shape_kwh
    flex *= rng.lognormal(0, 0.3, (H, T))
    cycle_steps = max(1, round(1.5 / dt_h))
    for h in range(H):
        for d in range(n_days):
            if rng.random() < 0.5:
                s = d * spd + rng.integers(round(9 / dt_h), round(21 / dt_h))
                flex[h, s : s + cycle_steps] += 2.0

    # --- Prices: PZU-like duck curve, retail import and prosumer export derived from it
    pzu_shape = (
        0.42
        + 0.18 * _gauss(hours, 8, 1.5)
        - 0.22 * (1 + 0.3 * season) * _gauss(hours, 13.5, 2.5)
        + 0.45 * _gauss(hours, 20, 1.8)
        - 0.10 * _gauss(hours, 3, 2.5)
    )
    level = np.repeat(rng.lognormal(0, 0.15, n_days), spd)
    pzu = np.clip(pzu_shape * level + rng.normal(0, 0.03, T), 0.02, None)
    price_import = pzu + RETAIL_ADDER
    price_export = pzu.copy()
    price_p2p = p2p_price_factor * price_import

    return Scenario(
        dt_h=dt_h,
        start=start,
        pv_kw=pv,
        load_crit_kw=crit,
        load_flex_kw=flex,
        price_import=price_import,
        price_export=price_export,
        price_p2p=price_p2p,
        seed=seed,
    )
