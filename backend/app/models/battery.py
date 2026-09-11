"""
Battery model - represents energy storage for a house
"""


class Battery:
    """
    Represents a home battery storage system
    
    Attributes:
        capacity_kwh: Total battery capacity in kWh
        soc_kwh: Current State of Charge in kWh
        soc_min_kwh: Minimum SOC (safety reserve)
        soc_max_kwh: Maximum SOC (typically same as capacity)
        p_ch_max_kw: Maximum charging power in kW
        p_dis_max_kw: Maximum discharging power in kW
    """
    
    def __init__(
        self,
        capacity_kwh: float = 20.0,
        soc_min_ratio: float = 0.2,
        p_ch_max_kw: float = 5.0,
        p_dis_max_kw: float = 5.0,
        initial_soc_ratio: float = 0.5
    ):
        self.capacity_kwh = capacity_kwh
        self.soc_max_kwh = capacity_kwh
        self.soc_min_kwh = capacity_kwh * soc_min_ratio
        self.p_ch_max_kw = p_ch_max_kw
        self.p_dis_max_kw = p_dis_max_kw
        self.soc_kwh = capacity_kwh * initial_soc_ratio
    
    def get_soc_ratio(self) -> float:
        """Get State of Charge as ratio (0.0 to 1.0)"""
        return self.soc_kwh / self.capacity_kwh
    
    def get_soc_percent(self) -> float:
        """Get State of Charge as percentage (0 to 100)"""
        return self.get_soc_ratio() * 100.0
    
    def can_discharge(self, power_kw: float, dt_h: float = 1.0) -> bool:
        """
        Check if battery can discharge given power for given time
        
        Args:
            power_kw: Power to discharge in kW
            dt_h: Time duration in hours
        
        Returns:
            True if discharge is possible without going below soc_min
        """
        energy_needed = power_kw * dt_h
        return (self.soc_kwh - energy_needed) >= self.soc_min_kwh
    
    def can_charge(self, power_kw: float, dt_h: float = 1.0) -> bool:
        """
        Check if battery can charge with given power for given time
        
        Args:
            power_kw: Power to charge in kW
            dt_h: Time duration in hours
        
        Returns:
            True if charge is possible without exceeding soc_max
        """
        energy_to_add = power_kw * dt_h
        return (self.soc_kwh + energy_to_add) <= self.soc_max_kwh
    
    def get_available_discharge_power(self, dt_h: float = 1.0) -> float:
        """
        Get maximum power that can be discharged right now
        
        Args:
            dt_h: Time duration in hours
        
        Returns:
            Maximum discharge power in kW
        """
        energy_available = self.soc_kwh - self.soc_min_kwh
        power_from_energy = energy_available / dt_h if dt_h > 0 else 0
        return min(self.p_dis_max_kw, power_from_energy)
    
    def get_available_charge_power(self, dt_h: float = 1.0) -> float:
        """
        Get maximum power that can be charged right now
        
        Args:
            dt_h: Time duration in hours
        
        Returns:
            Maximum charge power in kW
        """
        energy_space = self.soc_max_kwh - self.soc_kwh
        power_from_space = energy_space / dt_h if dt_h > 0 else 0
        return min(self.p_ch_max_kw, power_from_space)
    
    def charge(self, power_kw: float, dt_h: float = 1.0) -> float:
        """
        Charge battery with given power
        
        Args:
            power_kw: Power to charge in kW
            dt_h: Time duration in hours
        
        Returns:
            Actual power charged (may be less than requested)
        """
        max_power = self.get_available_charge_power(dt_h)
        actual_power = min(power_kw, max_power)
        self.soc_kwh += actual_power * dt_h
        self.soc_kwh = min(self.soc_kwh, self.soc_max_kwh)  # Clamp
        return actual_power
    
    def discharge(self, power_kw: float, dt_h: float = 1.0) -> float:
        """
        Discharge battery with given power
        
        Args:
            power_kw: Power to discharge in kW
            dt_h: Time duration in hours
        
        Returns:
            Actual power discharged (may be less than requested)
        """
        max_power = self.get_available_discharge_power(dt_h)
        actual_power = min(power_kw, max_power)
        self.soc_kwh -= actual_power * dt_h
        self.soc_kwh = max(self.soc_kwh, self.soc_min_kwh)  # Clamp
        return actual_power
    
    def to_dict(self, vpp_reserve_kwh: float = 0.0) -> dict:
        """
        Convert to dictionary for API responses.
        
        Args:
            vpp_reserve_kwh: Energy contributed to VPP reserve (from DB)
        """
        personal_soc = self.soc_kwh - vpp_reserve_kwh
        return {
            "capacity_kwh": self.capacity_kwh,
            "soc_kwh": round(self.soc_kwh, 2),
            "soc_percent": round(self.get_soc_percent(), 1),
            "personal_soc_kwh": round(max(0, personal_soc), 2),
            "vpp_reserve_kwh": round(vpp_reserve_kwh, 2),
            "soc_min_kwh": self.soc_min_kwh,
            "soc_max_kwh": self.soc_max_kwh,
            "p_ch_max_kw": self.p_ch_max_kw,
            "p_dis_max_kw": self.p_dis_max_kw
        }
    
    def __repr__(self):
        return f"Battery({self.capacity_kwh}kWh, SOC: {self.get_soc_percent():.1f}%)"
