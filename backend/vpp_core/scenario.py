"""Input time series (synthetic): step averages in kW over steps of dt_h hours, prices in lei/kWh."""
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
    pv_kw: np.ndarray          # (n_houses, n_steps) available PV power
    load_crit_kw: np.ndarray   # (n_houses, n_steps) critical load, never shed voluntarily
    load_flex_kw: np.ndarray   # (n_houses, n_steps) flexible load
    price_import: np.ndarray   # (n_steps,) lei/kWh
    price_export: np.ndarray   # (n_steps,) lei/kWh
    price_p2p: np.ndarray      # (n_steps,) lei/kWh
    seed: int | None = None

    def __post_init__(self) -> None:
        n_houses, n_steps = self.pv_kw.shape
        for name in ("load_crit_kw", "load_flex_kw"):
            if getattr(self, name).shape != (n_houses, n_steps):
                raise ValueError(f"{name} must have shape {(n_houses, n_steps)}")
        for name in ("price_import", "price_export", "price_p2p"):
            if getattr(self, name).shape != (n_steps,):
                raise ValueError(f"{name} must have shape {(n_steps,)}")
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


def _gauss(hours: np.ndarray, centre_h: float, width_h: float) -> np.ndarray:
    return np.exp(-((hours - centre_h) ** 2) / (2 * width_h**2))


def _season(day_of_year: np.ndarray) -> np.ndarray:
    """+1 at the summer solstice, -1 at the winter solstice."""
    return np.cos(2 * np.pi * (day_of_year - 172) / 365)


def steps_per_day_of(dt_h: float) -> int:
    steps = round(24 / dt_h)
    if abs(steps * dt_h - 24) > 1e-9:
        raise ValueError("24 h must be a whole number of steps")
    return steps


def pv_clear_sky_per_kwp(hours: np.ndarray, day_of_year: np.ndarray, latitude_deg: float) -> np.ndarray:
    """Clear-sky AC output (kW per kWp) from the solar elevation; tilt_gain ~1.55 in December, ~1.05 in June."""
    declination = np.radians(23.45) * np.sin(2 * np.pi * (284 + day_of_year) / 365)
    latitude = np.radians(latitude_deg)
    hour_angle = np.radians(15 * (hours - 12))
    sin_elevation = np.sin(latitude) * np.sin(declination) + np.cos(latitude) * np.cos(declination) * np.cos(hour_angle)
    sin_elevation = np.clip(sin_elevation, 0, None)
    tilt_gain = 1.30 - 0.25 * _season(day_of_year)
    return PERFORMANCE_RATIO * tilt_gain * sin_elevation**1.15


def _sky_clearness(
    weather: Weather, day_doy: np.ndarray, n_steps: int, spd: int, rng: np.random.Generator
) -> np.ndarray:
    """(n_steps,) factor in [0, 1]: daily clearness index x intra-day AR(1) cloud noise, same sky for all houses."""
    if weather == "clear":
        return np.ones(n_steps)
    if weather == "cloudy":
        return np.full(n_steps, 0.3)
    mean_clearness = 0.62 + 0.12 * _season(day_doy)
    clearness = rng.beta(mean_clearness * 6, (1 - mean_clearness) * 6)
    sky = np.repeat(np.clip(clearness, 0.05, 1.0), spd)
    noise = np.zeros(n_steps)
    for t in range(1, n_steps):
        noise[t] = 0.8 * noise[t - 1] + rng.normal(0, 0.12)
    return np.clip(sky * np.exp(noise * (1.2 - sky)), 0.02, 1.0)


def _pv_profile(
    community: CommunityParams, hours: np.ndarray, doy: np.ndarray, latitude_deg: float,
    sky: np.ndarray, rng: np.random.Generator,
) -> np.ndarray:
    """(n_houses, n_steps) kW."""
    unit_kw = pv_clear_sky_per_kwp(hours, doy, latitude_deg) * sky
    kwp = np.array([house.pv_kwp for house in community.houses])
    orientation = rng.uniform(0.92, 1.05, community.n_houses)
    return np.outer(kwp * orientation, unit_kw)


def _load_profile(
    n_houses: int, n_days: int, spd: int, dt_h: float, hours: np.ndarray, season: np.ndarray,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """(critical, flexible), each (n_houses, n_steps) kW; on half of the days a 2 kW / 1.5 h appliance cycle."""
    n_steps = n_days * spd
    shape = 0.35 + 0.8 * _gauss(hours, 7.5, 1.2) + 0.5 * _gauss(hours, 13, 2.0) + 1.3 * _gauss(hours, 20, 2.0)
    critical = np.repeat(rng.uniform(0.10, 0.22, n_houses)[:, None], n_steps, axis=1)
    daily_kwh = rng.uniform(6.0, 11.0, n_houses)[:, None] * (1 - 0.15 * season)[None, :]
    day_shape_kwh = shape[:spd].sum() * dt_h
    flex_kwh = np.clip(daily_kwh - critical * 24, 0.5, None)
    flexible = flex_kwh * shape[None, :] / day_shape_kwh
    flexible *= rng.lognormal(0, 0.3, (n_houses, n_steps))
    cycle_steps = max(1, round(1.5 / dt_h))
    for h in range(n_houses):
        for d in range(n_days):
            if rng.random() < 0.5:
                cycle_start = d * spd + rng.integers(round(9 / dt_h), round(21 / dt_h))
                flexible[h, cycle_start : cycle_start + cycle_steps] += 2.0
    return critical, flexible


def _price_profile(
    hours: np.ndarray, season: np.ndarray, n_days: int, spd: int, p2p_price_factor: float,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(import, export, p2p), each (n_steps,): import = PZU + RETAIL_ADDER, export = PZU, p2p = factor x import."""
    n_steps = n_days * spd
    pzu_shape = (
        0.42
        + 0.18 * _gauss(hours, 8, 1.5)
        - 0.22 * (1 + 0.3 * season) * _gauss(hours, 13.5, 2.5)
        + 0.45 * _gauss(hours, 20, 1.8)
        - 0.10 * _gauss(hours, 3, 2.5)
    )
    daily_level = np.repeat(rng.lognormal(0, 0.15, n_days), spd)
    pzu = np.clip(pzu_shape * daily_level + rng.normal(0, 0.03, n_steps), 0.02, None)
    price_import = pzu + RETAIL_ADDER
    price_export = pzu.copy()
    price_p2p = p2p_price_factor * price_import
    return price_import, price_export, price_p2p


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
    spd = steps_per_day_of(dt_h)
    rng = np.random.default_rng(seed)
    n_houses, n_steps = community.n_houses, n_days * spd

    hours = (np.arange(n_steps) % spd + 0.5) * dt_h    # step midpoints, hour of the day
    day_doy = np.array([(start + timedelta(days=d)).timetuple().tm_yday for d in range(n_days)])
    doy = np.repeat(day_doy, spd)
    season = _season(doy)

    sky = _sky_clearness(weather, day_doy, n_steps, spd, rng)
    pv = _pv_profile(community, hours, doy, latitude_deg, sky, rng)
    critical, flexible = _load_profile(n_houses, n_days, spd, dt_h, hours, season, rng)
    price_import, price_export, price_p2p = _price_profile(hours, season, n_days, spd, p2p_price_factor, rng)

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
