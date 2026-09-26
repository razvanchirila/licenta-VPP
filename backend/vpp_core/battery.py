"""Physical model of one household battery. Powers in kW (AC side), energy in kWh, dt_h in hours."""
from __future__ import annotations

from vpp_core.params import BatteryParams

TOL = 1e-6   # kW / kWh tolerance for floating-point noise in feasibility checks


class PhysicalLimitError(ValueError):
    """Requested power or resulting SOC outside the physical limits."""


class Battery:
    def __init__(self, params: BatteryParams, soc_kwh: float):
        if not params.soc_min_kwh - TOL <= soc_kwh <= params.soc_max_kwh + TOL:
            raise PhysicalLimitError(f"initial SOC {soc_kwh} outside limits")
        self.params = params
        self.soc_kwh = soc_kwh

    def max_charge_kw(self, dt_h: float) -> float:
        params = self.params
        room_kw = (params.soc_max_kwh - self.soc_kwh) / (params.eta_ch * dt_h)
        return max(0.0, min(params.p_ch_max_kw, room_kw))

    def max_discharge_kw(self, dt_h: float) -> float:
        params = self.params
        available_kw = (self.soc_kwh - params.soc_min_kwh) * params.eta_dis / dt_h
        return max(0.0, min(params.p_dis_max_kw, available_kw))

    def next_soc(self, charge_kw: float, discharge_kw: float, dt_h: float) -> float:
        # soc[t+1] = soc[t] + (eta_ch * ch - dis / eta_dis) * dt  (same equation as the LP constraint)
        params = self.params
        return self.soc_kwh + (params.eta_ch * charge_kw - discharge_kw / params.eta_dis) * dt_h

    def apply(self, charge_kw: float, discharge_kw: float, dt_h: float) -> float:
        params = self.params
        if charge_kw < -TOL or discharge_kw < -TOL:
            raise PhysicalLimitError("negative battery power")
        if charge_kw > params.p_ch_max_kw + TOL:
            raise PhysicalLimitError(f"charge {charge_kw:.4f} kW > limit {params.p_ch_max_kw} kW")
        if discharge_kw > params.p_dis_max_kw + TOL:
            raise PhysicalLimitError(f"discharge {discharge_kw:.4f} kW > limit {params.p_dis_max_kw} kW")
        soc = self.next_soc(charge_kw, discharge_kw, dt_h)
        if soc < params.soc_min_kwh - TOL or soc > params.soc_max_kwh + TOL:
            raise PhysicalLimitError(
                f"SOC would be {soc:.4f} kWh, outside [{params.soc_min_kwh}, {params.soc_max_kwh}]"
            )
        self.soc_kwh = min(max(soc, params.soc_min_kwh), params.soc_max_kwh)
        return self.soc_kwh

    def losses_kwh(self, charge_kw: float, discharge_kw: float, dt_h: float) -> float:
        """Conversion losses (kWh) of one step."""
        params = self.params
        return (charge_kw * (1 - params.eta_ch) + discharge_kw * (1 / params.eta_dis - 1)) * dt_h
