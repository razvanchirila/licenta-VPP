"""
Static parameters of the community: batteries, houses, grid connection.

Units: power in kW, energy in kWh, time in hours, prices in lei/kWh.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

Mode = Literal["Eco", "Profit"]


@dataclass(frozen=True)
class BatteryParams:
    capacity_kwh: float = 20.0
    soc_min_ratio: float = 0.2
    p_ch_max_kw: float = 5.0
    p_dis_max_kw: float = 5.0
    eta_ch: float = 0.95   # round-trip efficiency = eta_ch * eta_dis (~0.90)
    eta_dis: float = 0.95

    def __post_init__(self):
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
    mode: Mode = "Eco"
    p2p_enabled: bool = True
    initial_soc_ratio: float = 0.5

    def __post_init__(self):
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
    """Limits at the community's connection point (transformer) and internal line."""
    import_max_kw: float = math.inf
    export_max_kw: float = math.inf
    internal_line_kw: float = math.inf


@dataclass(frozen=True)
class CommunityParams:
    houses: tuple[HouseParams, ...]
    grid: GridParams = field(default_factory=GridParams)

    def __post_init__(self):
        ids = [h.id for h in self.houses]
        if len(set(ids)) != len(ids):
            raise ValueError("house ids must be unique")

    @property
    def n_houses(self) -> int:
        return len(self.houses)


def default_community() -> CommunityParams:
    """The E.ON competition setup: 10 houses x 10 kWp, batteries (20 kWh) on 8 of them.

    Grid limits are sized like a small distribution transformer so they actually bind
    at midday (100 kWp installed vs. 40 kW export).
    """
    houses = tuple(
        HouseParams(
            id=i,
            pv_kwp=10.0,
            battery=BatteryParams() if i <= 8 else None,
            mode="Eco" if i % 2 else "Profit",
        )
        for i in range(1, 11)
    )
    return CommunityParams(
        houses=houses,
        grid=GridParams(import_max_kw=50.0, export_max_kw=40.0, internal_line_kw=30.0),
    )
