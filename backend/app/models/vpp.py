"""
VPP (Virtual Power Plant) model - manages the neighborhood of houses
"""
from typing import List
from app.models.house import House


class VPP:
    """
    Virtual Power Plant - manages a neighborhood of houses
    
    Attributes:
        houses: List of houses in the VPP
        p_grid_import_max_kw: Maximum import from grid (kW)
        p_grid_export_max_kw: Maximum export to grid (kW)
        p_internal_line_limit_kw: Maximum power on internal network lines (kW)
    """
    
    def __init__(
        self,
        houses: List[House] = None,
        p_grid_import_max_kw: float = 2000.0,
        p_grid_export_max_kw: float = 1500.0,
        p_internal_line_limit_kw: float = 1000.0
    ):
        self.houses = houses if houses is not None else []
        self.p_grid_import_max_kw = p_grid_import_max_kw
        self.p_grid_export_max_kw = p_grid_export_max_kw
        self.p_internal_line_limit_kw = p_internal_line_limit_kw
    
    def add_house(self, house: House):
        """Add a house to the VPP"""
        self.houses.append(house)
    
    def remove_house(self, house_id: int):
        """Remove a house by ID"""
        self.houses = [h for h in self.houses if h.id != house_id]
    
    def get_house(self, house_id: int) -> House:
        """Get house by ID"""
        for house in self.houses:
            if house.id == house_id:
                return house
        return None
    
    def get_total_pv_capacity(self) -> float:
        """Get total PV capacity across all houses"""
        return sum(h.pv_capacity_kw for h in self.houses if h.has_pv)
    
    def get_total_battery_capacity(self) -> float:
        """Get total battery capacity across all houses"""
        return sum(h.battery.capacity_kwh for h in self.houses if h.battery)
    
    def get_total_battery_soc(self) -> float:
        """Get total battery SOC across all houses"""
        return sum(h.battery.soc_kwh for h in self.houses if h.battery)
    
    def get_houses_with_battery(self) -> List[House]:
        """Get list of houses that have batteries"""
        return [h for h in self.houses if h.battery is not None]
    
    def get_houses_without_battery(self) -> List[House]:
        """Get list of houses without batteries"""
        return [h for h in self.houses if h.battery is None]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "total_houses": len(self.houses),
            "houses_with_battery": len(self.get_houses_with_battery()),
            "houses_without_battery": len(self.get_houses_without_battery()),
            "total_pv_capacity_kw": round(self.get_total_pv_capacity(), 2),
            "total_battery_capacity_kwh": round(self.get_total_battery_capacity(), 2),
            "total_battery_soc_kwh": round(self.get_total_battery_soc(), 2),
            "p_grid_import_max_kw": self.p_grid_import_max_kw,
            "p_grid_export_max_kw": self.p_grid_export_max_kw,
            "p_internal_line_limit_kw": self.p_internal_line_limit_kw
        }
    
    def __repr__(self):
        return f"VPP({len(self.houses)} houses, {len(self.get_houses_with_battery())} with batteries)"
