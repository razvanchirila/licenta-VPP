"""Static parameters of the community: batteries, houses, grid connection. Units: kW, kWh, hours, lei/kWh."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Literal

import numpy as np

Mode = Literal["Eco", "Profit"]


# Deye SE-F16 module (LiFePO4, 51.2 V): 16 kWh, DoD 90 %, 160 A charge ~ 8 kW; the hybrid inverter's
# battery port caps a parallel bank at 10 kW (sources in backend/data/README.md)
DEYE_MODULE_KWH = 16.0
DEYE_MODULE_KW = 8.0
DEYE_BANK_KW_MAX = 10.0
INVERTER_KW = 10.0


@dataclass(frozen=True)
class BatteryParams:
    """Defaults = one Deye SE-F16 module. Round-trip efficiency = eta_ch * eta_dis (~0.90)."""

    capacity_kwh: float = DEYE_MODULE_KWH
    soc_min_ratio: float = 0.1     # depth of discharge 90 %
    p_ch_max_kw: float = DEYE_MODULE_KW
    p_dis_max_kw: float = DEYE_MODULE_KW
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


def deye_se_f16(modules: int) -> BatteryParams | None:
    """`modules` SE-F16 in parallel: 16 kWh each, 8 kW per module up to the 10 kW of the inverter; 0 -> None."""
    if modules < 0:
        raise ValueError("modules must be >= 0")
    if modules == 0:
        return None
    power_kw = min(DEYE_MODULE_KW * modules, DEYE_BANK_KW_MAX)
    return BatteryParams(capacity_kwh=DEYE_MODULE_KWH * modules, p_ch_max_kw=power_kw, p_dis_max_kw=power_kw)


@dataclass(frozen=True)
class HouseParams:
    """inverter_kw bounds the net AC power of the house in both directions:
    |(pv - curtail) + dis - ch| <= inverter_kw (math.inf = no limit)."""

    id: int
    pv_kwp: float = 10.0
    battery: BatteryParams | None = None
    mode: Mode = "Eco"             # used by the rule-based controller only
    p2p_enabled: bool = True
    initial_soc_ratio: float = 0.5
    inverter_kw: float = INVERTER_KW

    def __post_init__(self) -> None:
        if self.pv_kwp < 0:
            raise ValueError("pv_kwp must be >= 0")
        if not self.inverter_kw > 0:
            raise ValueError("inverter_kw must be > 0")
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


DEFAULT_MODULES = (1, 1, 1, 1, 1, 2, 2, 2, 0, 0)   # SE-F16 modules of houses 1..10


def default_community() -> CommunityParams:
    """10 houses x 10 kWp with 10 kW inverters; 5 with one SE-F16 module, 3 with two, the last 2 without battery;
    grid limits sized so they bind at midday (100 kWp vs 40 kW)."""
    houses = tuple(
        HouseParams(
            id=house_id,
            pv_kwp=10.0,
            battery=deye_se_f16(modules),
            mode="Eco" if house_id % 2 else "Profit",
        )
        for house_id, modules in enumerate(DEFAULT_MODULES, start=1)
    )
    return CommunityParams(
        houses=houses,
        grid=GridParams(import_max_kw=50.0, export_max_kw=40.0, internal_line_kw=30.0),
    )


PV_KWP_CHOICES = (5.0, 6.0, 8.0, 10.0, 12.0)
MODULE_PROBABILITIES = (0.2, 0.5, 0.3)   # 0 / 1 / 2 SE-F16 modules
# grid limits per house (kW): the default 10-house community has 50 / 40 / 30
IMPORT_KW_PER_HOUSE, EXPORT_KW_PER_HOUSE, LINE_KW_PER_HOUSE = 5.0, 4.0, 3.0


def random_community(n_houses: int, seed: int = 0) -> CommunityParams:
    """Mixed community for the scaling study: PV 5-12 kWp, 0 / 1 / 2 SE-F16 modules with probabilities
    MODULE_PROBABILITIES, random mode; grid limits proportional to n_houses."""
    if n_houses < 1:
        raise ValueError("n_houses must be >= 1")
    rng = np.random.default_rng(seed)
    houses = []
    for house_id in range(1, n_houses + 1):
        modules = int(rng.choice(len(MODULE_PROBABILITIES), p=MODULE_PROBABILITIES))
        houses.append(HouseParams(
            id=house_id, pv_kwp=float(rng.choice(PV_KWP_CHOICES)), battery=deye_se_f16(modules),
            mode="Eco" if rng.random() < 0.5 else "Profit",
        ))
    return CommunityParams(
        houses=tuple(houses),
        grid=GridParams(
            import_max_kw=IMPORT_KW_PER_HOUSE * n_houses, export_max_kw=EXPORT_KW_PER_HOUSE * n_houses,
            internal_line_kw=LINE_KW_PER_HOUSE * n_houses,
        ),
    )
