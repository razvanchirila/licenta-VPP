"""
Physical battery model. It never decides anything: it only checks that a requested
(charge, discharge) pair is feasible for one step and updates the state of charge.
"""
from __future__ import annotations

from vpp_core.params import BatteryParams

TOL = 1e-6


class PhysicalLimitError(ValueError):
    pass


class Battery:
    def __init__(self, params: BatteryParams, soc_kwh: float):
        if not params.soc_min_kwh - TOL <= soc_kwh <= params.soc_max_kwh + TOL:
            raise PhysicalLimitError(f"initial SOC {soc_kwh} outside limits")
        self.params = params
        self.soc_kwh = soc_kwh

    def max_charge_kw(self, dt_h: float) -> float:
        """Largest charging power (AC side) for one step, limited by power and free space."""
        p = self.params
        room = (p.soc_max_kwh - self.soc_kwh) / (p.eta_ch * dt_h)
        return max(0.0, min(p.p_ch_max_kw, room))

    def max_discharge_kw(self, dt_h: float) -> float:
        """Largest discharging power (AC side) for one step, limited by power and stored energy."""
        p = self.params
        avail = (self.soc_kwh - p.soc_min_kwh) * p.eta_dis / dt_h
        return max(0.0, min(p.p_dis_max_kw, avail))

    def next_soc(self, ch_kw: float, dis_kw: float, dt_h: float) -> float:
        p = self.params
        return self.soc_kwh + (p.eta_ch * ch_kw - dis_kw / p.eta_dis) * dt_h

    def apply(self, ch_kw: float, dis_kw: float, dt_h: float) -> float:
        """Apply one step; raises PhysicalLimitError if the request is infeasible."""
        p = self.params
        if ch_kw < -TOL or dis_kw < -TOL:
            raise PhysicalLimitError("negative battery power")
        if ch_kw > p.p_ch_max_kw + TOL:
            raise PhysicalLimitError(f"charge {ch_kw:.4f} kW > limit {p.p_ch_max_kw} kW")
        if dis_kw > p.p_dis_max_kw + TOL:
            raise PhysicalLimitError(f"discharge {dis_kw:.4f} kW > limit {p.p_dis_max_kw} kW")
        soc = self.next_soc(ch_kw, dis_kw, dt_h)
        if soc < p.soc_min_kwh - TOL or soc > p.soc_max_kwh + TOL:
            raise PhysicalLimitError(
                f"SOC would be {soc:.4f} kWh, outside [{p.soc_min_kwh}, {p.soc_max_kwh}]"
            )
        self.soc_kwh = min(max(soc, p.soc_min_kwh), p.soc_max_kwh)
        return self.soc_kwh

    def losses_kwh(self, ch_kw: float, dis_kw: float, dt_h: float) -> float:
        p = self.params
        return (ch_kw * (1 - p.eta_ch) + dis_kw * (1 / p.eta_dis - 1)) * dt_h
