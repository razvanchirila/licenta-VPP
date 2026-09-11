"""
Device model - represents an appliance/device in a house
"""
from datetime import datetime
from typing import Optional, Union


class Device:
    """
    Represents an electrical device/appliance with energy metering.
    
    Attributes:
        id: Unique identifier
        name: Device name (e.g., "Frigider", "TV")
        power_w: Power consumption in Watts
        critical: Whether device is critical (cannot be turned off)
        status_on: Current on/off status
        last_state_change_ts: DateTime of last state change
        accumulated_energy_kwh: Total energy consumed (saved to DB)
    """
    
    def __init__(
        self, 
        id: int, 
        name: str, 
        power_w: float, 
        critical: bool = False, 
        status_on: bool = False,
        last_state_change_ts: Optional[Union[datetime, float]] = None,
        accumulated_energy_kwh: float = 0.0
    ):
        self.id = id
        self.name = name
        self.power_w = power_w
        self.critical = critical
        self.status_on = status_on
        # Convert float timestamp to datetime if needed
        if isinstance(last_state_change_ts, (int, float)):
            self.last_state_change_ts = datetime.fromtimestamp(last_state_change_ts)
        else:
            self.last_state_change_ts = last_state_change_ts
        self.accumulated_energy_kwh = accumulated_energy_kwh
    
    def get_power_kw(self) -> float:
        """
        Get current power consumption in kW
        Returns 0 if device is off
        """
        if self.status_on:
            return self.power_w / 1000.0
        return 0.0
    
    def calculate_pending_energy(self, sim_datetime: Optional[datetime] = None) -> float:
        """
        Calculate energy consumed since last state change for ON devices.
        Returns 0 if device is OFF.
        
        Args:
            sim_datetime: Simulation datetime to use (defaults to current sim time)
        """
        if not self.status_on or not self.last_state_change_ts:
            return 0.0
        
        # Use simulation time if available
        if sim_datetime is None:
            try:
                from app.services.simulation_loop import simulation_loop
                sim_datetime = simulation_loop.clock.sim_datetime
            except Exception:
                sim_datetime = datetime.now()
        
        duration = sim_datetime - self.last_state_change_ts
        duration_hours = duration.total_seconds() / 3600
        return self.get_power_kw() * duration_hours
    
    def toggle(self, sim_datetime: Optional[datetime] = None) -> float:
        """
        Toggle device on/off status with energy calculation.
        Returns energy calculated when turning OFF.
        
        Args:
            sim_datetime: Simulation datetime to use (defaults to current sim time)
        """
        energy_calculated = 0.0
        
        # Use simulation time if available
        if sim_datetime is None:
            try:
                from app.services.simulation_loop import simulation_loop
                sim_datetime = simulation_loop.clock.sim_datetime
            except Exception:
                sim_datetime = datetime.now()
        
        if not self.critical or not self.status_on:
            if self.status_on and self.last_state_change_ts:
                # Turning OFF - calculate energy consumed
                duration = sim_datetime - self.last_state_change_ts
                duration_hours = duration.total_seconds() / 3600
                energy_calculated = self.get_power_kw() * duration_hours
                self.accumulated_energy_kwh += energy_calculated
            
            self.status_on = not self.status_on
            self.last_state_change_ts = sim_datetime
        
        return energy_calculated
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "name": self.name,
            "power_w": self.power_w,
            "critical": self.critical,
            "status_on": self.status_on,
            "current_power_kw": self.get_power_kw(),
            "last_state_change_ts": self.last_state_change_ts.isoformat() if self.last_state_change_ts else None,
            "accumulated_energy_kwh": round(self.accumulated_energy_kwh, 6),
            "pending_energy_kwh": round(self.calculate_pending_energy(), 6)
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Device':
        """Create Device from dictionary (deserialization)."""
        return cls(
            id=data["id"],
            name=data["name"],
            power_w=data["power_w"],
            critical=data.get("critical", False),
            status_on=data.get("status_on", False),
            last_state_change_ts=data.get("last_state_change_ts"),
            accumulated_energy_kwh=data.get("accumulated_energy_kwh", 0.0)
        )
    
    def __repr__(self):
        status = "ON" if self.status_on else "OFF"
        crit = "CRITICAL" if self.critical else "NON-CRITICAL"
        return f"Device({self.name}, {self.power_w}W, {crit}, {status})"
