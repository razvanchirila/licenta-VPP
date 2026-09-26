"""Static parameters of the community: batteries, houses, grid connection. Units: kW, kWh, hours, lei/kWh."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

Mode = Literal["Eco", "Profit"]


@dataclass(frozen=True)
class BatteryParams:
    """Round-trip efficiency = eta_ch * eta_dis (~0.90)."""

    capacity_kwh: float = 20.0
    soc_min_ratio: float = 0.2     # depth of discharge 80 %
    p_ch_max_kw: float = 5.0
    p_dis_max_kw: float = 5.0
    eta_ch: float = 0.95
    eta_dis: float = 0.95

    def __post_init__(self) -> None:
        if self.capacity_kwh <= 0:
            raise ValueError("capacity_kwh must be > 0")
        if not 0 <= self.soc_min_ratio < 1:
            raise ValueError("soc_min_ratio must be in [0, 1)")
        if self.p_ch_max_kw < 0 or self.p_dis_max_kw < 0:
            raise ValueError("power limits must be >= 0")
        if not (0 < self.eta_ch <= 1 and 0 < self.eta_dis <= 1):
            raise ValueError("efficiencies must be in (0, 1]")

    @property
    def soc_min_kwh(self) -> float:
        return self.capacity_kwh * self.soc_min_ratio

    @property
    def soc_max_kwh(self) -> float:
        return self.capacity_kwh

    @property
    def usable_kwh(self) -> float:
        return self.soc_max_kwh - self.soc_min_kwh


@dataclass(frozen=True)
class HouseParams:
    id: int
    pv_kwp: float = 10.0
    battery: BatteryParams | None = None
    mode: Mode = "Eco"             # used by the rule-based controller only
    p2p_enabled: bool = True
    initial_soc_ratio: float = 0.5

    def __post_init__(self) -> None:
        if self.pv_kwp < 0:
            raise ValueError("pv_kwp must be >= 0")
        if self.mode not in ("Eco", "Profit"):
            raise ValueError(f"invalid mode {self.mode!r}")
        if self.battery is not None and not (
            self.battery.soc_min_ratio <= self.initial_soc_ratio <= 1
        ):
            raise ValueError("initial_soc_ratio must be within [soc_min_ratio, 1]")

    @property
    def initial_soc_kwh(self) -> float:
        return self.battery.capacity_kwh * self.initial_soc_ratio if self.battery else 0.0


@dataclass(frozen=True)
class GridParams:
    """Community-wide limits (kW): grid connection point and internal P2P line."""

    import_max_kw: float = math.inf
    export_max_kw: float = math.inf
    internal_line_kw: float = math.inf


@dataclass(frozen=True)
class CommunityParams:
    houses: tuple[HouseParams, ...]
    grid: GridParams = field(default_factory=GridParams)

    def __post_init__(self) -> None:
        ids = [house.id for house in self.houses]
        if len(set(ids)) != len(ids):
            raise ValueError("house ids must be unique")

    @property
    def n_houses(self) -> int:
        return len(self.houses)


def default_community() -> CommunityParams:
    """10 houses x 10 kWp, batteries on houses 1-8; grid limits sized so they bind at midday (100 kWp vs 40 kW)."""
    houses = tuple(
        HouseParams(
            id=house_id,
            pv_kwp=10.0,
            battery=BatteryParams() if house_id <= 8 else None,
            mode="Eco" if house_id % 2 else "Profit",
        )
        for house_id in range(1, 11)
    )
    return CommunityParams(
        houses=houses,
        grid=GridParams(import_max_kw=50.0, export_max_kw=40.0, internal_line_kw=30.0),
    )


PV_KWP_CHOICES = (5.0, 6.0, 8.0, 10.0, 12.0)
BATTERY_KWH_CHOICES = (10.0, 15.0, 20.0)
BATTERY_PROBABILITY = 0.8
# grid limits per house (kW): the default 10-house community has 50 / 40 / 30
IMPORT_KW_PER_HOUSE, EXPORT_KW_PER_HOUSE, LINE_KW_PER_HOUSE = 5.0, 4.0, 3.0


def random_community(n_houses: int, seed: int = 0) -> CommunityParams:
    """Mixed community for the scaling study: PV 5-12 kWp, a battery of 10-20 kWh on ~80 % of the houses
    (C/4 charge and discharge), random mode; grid limits proportional to n_houses."""
    if n_houses < 1:
        raise ValueError("n_houses must be >= 1")
    rng = np.random.default_rng(seed)
    houses = []
    for house_id in range(1, n_houses + 1):
        battery = None
        if rng.random() < BATTERY_PROBABILITY:
            capacity = float(rng.choice(BATTERY_KWH_CHOICES))
            battery = BatteryParams(capacity_kwh=capacity, p_ch_max_kw=capacity / 4, p_dis_max_kw=capacity / 4)
        houses.append(HouseParams(
            id=house_id, pv_kwp=float(rng.choice(PV_KWP_CHOICES)), battery=battery,
            mode="Eco" if rng.random() < 0.5 else "Profit",
        ))
    return CommunityParams(
        houses=tuple(houses),
        grid=GridParams(
            import_max_kw=IMPORT_KW_PER_HOUSE * n_houses, export_max_kw=EXPORT_KW_PER_HOUSE * n_houses,
            internal_line_kw=LINE_KW_PER_HOUSE * n_houses,
        ),
    )
