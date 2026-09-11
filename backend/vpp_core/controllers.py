"""
Control strategies. A controller only decides; the simulator checks and applies.

RuleBasedController is the competition algorithm (inceput2.md) with its bugs fixed.
With some features switched off it also gives the reference baselines
(no battery, battery without VPP, ...), see experiments.baseline_controllers().
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from vpp_core.dispatch import Dispatch
from vpp_core.params import CommunityParams
from vpp_core.scenario import Scenario

# Share of the non-critical load that is kept, per mode and price zone (inceput2.md §5)
ALPHA = {
    "Eco": {"cheap": 1.0, "normal": 0.6, "expensive": 0.3},
    "Profit": {"cheap": 0.8, "normal": 0.4, "expensive": 0.1},
}


class Controller(ABC):
    name = "controller"

    def reset(self, community: CommunityParams, scenario: Scenario) -> None:
        self.community = community
        self.scenario = scenario

    @abstractmethod
    def dispatch(self, state) -> Dispatch: ...


def price_zones(price: np.ndarray, steps_per_day: int, cheap_q: float, expensive_q: float) -> np.ndarray:
    """'cheap' / 'normal' / 'expensive' per step, using quantiles of each day's prices.

    Relative thresholds (the spec's indices_cheap / indices_expensive) instead of fixed
    lei values, so the zones exist whatever the absolute price level is.
    """
    zones = np.full(price.shape, "normal", dtype=object)
    for s in range(0, len(price), steps_per_day):
        day = price[s : s + steps_per_day]
        lo, hi = np.quantile(day, [cheap_q, expensive_q])
        zones[s : s + steps_per_day][day <= lo] = "cheap"
        zones[s : s + steps_per_day][day >= hi] = "expensive"
    return zones


class RuleBasedController(Controller):
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

    def reset(self, community, scenario):
        super().reset(community, scenario)
        houses = community.houses
        self.zones = price_zones(
            scenario.price_import, scenario.steps_per_day, self.cheap_quantile, self.expensive_quantile
        )
        self.p2p_mask = np.array([h.p2p_enabled for h in houses], dtype=float)
        self.profit = np.array([h.mode == "Profit" for h in houses])
        self.has_batt = np.array([h.battery is not None for h in houses])
        self.capacity = np.array([h.battery.capacity_kwh if h.battery else 0.0 for h in houses])
        self.eta_ch = np.array([h.battery.eta_ch if h.battery else 1.0 for h in houses])

    def dispatch(self, state) -> Dispatch:
        sc, g, t, dt = self.scenario, self.community.grid, state.t, self.scenario.dt_h
        H = self.community.n_houses
        pv, crit, flex = sc.pv_kw[:, t], sc.load_crit_kw[:, t], sc.load_flex_kw[:, t]
        d = Dispatch.zeros(H)

        # 1. Mode/price flexibility: drop part of the non-critical load (spec §5)
        if self.apply_alpha:
            zone = self.zones[t]
            alpha = np.array([ALPHA[h.mode][zone] for h in self.community.houses])
            d.shed = (1 - alpha) * flex
        load = crit + flex - d.shed

        # 2. PV covers own load first
        direct = np.minimum(pv, load)
        surplus = pv - direct
        deficit = load - direct

        max_ch = state.max_charge_kw(dt) if self.use_battery else np.zeros(H)
        max_dis = state.max_discharge_kw(dt) if self.use_battery else np.zeros(H)

        def battery():
            nonlocal surplus, deficit
            d.dis = np.minimum(deficit, max_dis)
            deficit = deficit - d.dis
            d.ch = np.minimum(surplus, max_ch)
            surplus = surplus - d.ch

        def p2p():
            nonlocal surplus, deficit
            if not self.p2p:
                return
            S, D = surplus * self.p2p_mask, deficit * self.p2p_mask
            traded = min(S.sum(), D.sum(), g.internal_line_kw)  # kW vs kW
            if traded <= 0:
                return
            out, inn = S * (traded / S.sum()), D * (traded / D.sum())
            d.p2p_out, d.p2p_in = out, inn
            surplus, deficit = surplus - out, deficit - inn

        # 3-4. Battery and neighbours; the spec order is battery first
        if self.p2p_before_battery:
            p2p(); battery()
        else:
            battery(); p2p()

        # 5. Remaining surplus -> grid export (community limit), the rest is curtailed
        d.exp = surplus.copy()
        if d.exp.sum() > g.export_max_kw:
            d.exp *= g.export_max_kw / d.exp.sum()
        d.curtail = surplus - d.exp

        # 6. Remaining deficit -> grid import; above the limit, load is shed (and reported)
        d.imp = deficit.copy()
        if d.imp.sum() > g.import_max_kw:
            d.imp *= g.import_max_kw / d.imp.sum()
            d.shed = d.shed + (deficit - d.imp)

        # 7. Arbitrage: Profit houses charge from the grid in cheap hours, within the
        #    battery's remaining power budget for this step and the import headroom
        if self.arbitrage and self.use_battery and self.zones[t] == "cheap":
            cand = self.profit & self.has_batt & (d.dis <= 0)
            target = (self.arbitrage_target_ratio * self.capacity - state.soc_kwh) / (self.eta_ch * dt)
            want = np.where(cand, np.clip(np.minimum(max_ch - d.ch, target), 0, None), 0.0)
            room = max(g.import_max_kw - d.imp.sum(), 0.0)
            if want.sum() > room:
                want *= room / want.sum()
            d.ch = d.ch + want
            d.imp = d.imp + want

        return d
