"""
House model - represents a house with devices, battery, and PV system
"""
from typing import List, Optional
from app.models.device import Device
from app.models.battery import Battery


class House:
    """
    Represents a house in the VPP network
    
    Attributes:
        id: Unique identifier
        devices: List of electrical devices
        battery: Battery system (optional)
        mode: Operating mode ("Eco" or "Profit")
        has_pv: Whether house has PV system
        pv_capacity_kw: PV system capacity in kW
        selling_enabled: Whether house can sell to neighbors (P2P trading)
        buying_enabled: Whether house can buy from neighbors (P2P trading)
        trading_price_mode: "fixed" or "discount"
        trading_fixed_price: Fixed price in lei/kWh (when price_mode="fixed")
        trading_discount_percent: Discount from grid price (when price_mode="discount")
    """
    
    def __init__(
        self,
        id: int,
        devices: List[Device] = None,
        battery: Optional[Battery] = None,
        mode: str = "Eco",
        has_pv: bool = True,
        pv_capacity_kw: float = 10.0,
        selling_enabled: bool = True,
        buying_enabled: bool = True,
        trading_price_mode: str = "discount",
        trading_fixed_price: Optional[float] = None,
        trading_discount_percent: float = 20.0
    ):
        self.id = id
        self.devices = devices if devices is not None else []
        self.battery = battery
        self.mode = mode  # "Eco" or "Profit"
        self.has_pv = has_pv
        self.pv_capacity_kw = pv_capacity_kw
        # P2P Trading settings
        self.selling_enabled = selling_enabled
        self.buying_enabled = buying_enabled
        self.trading_price_mode = trading_price_mode
        self.trading_fixed_price = trading_fixed_price
        self.trading_discount_percent = trading_discount_percent
    
    def compute_L_crit_kw(self) -> float:
        """
        Calculate critical load (devices that cannot be turned off)
        
        Returns:
            Critical load in kW
        """
        return sum(d.get_power_kw() for d in self.devices if d.critical and d.status_on)
    
    def compute_L_noncrit_kw(self) -> float:
        """
        Calculate non-critical load (devices that can be turned off)
        
        Returns:
            Non-critical load in kW
        """
        return sum(d.get_power_kw() for d in self.devices if not d.critical and d.status_on)
    
    def apply_mode_and_price(self, price_zone: str) -> float:
        """
        Calculate alpha factor based on mode and price zone
        Alpha scales the non-critical consumption
        
        Args:
            price_zone: "cheap", "normal", or "expensive"
        
        Returns:
            Alpha factor (0.0 to 1.0)
        """
        if self.mode == "Eco":
            if price_zone == "expensive":
                return 0.3
            elif price_zone == "normal":
                return 0.6
            else:  # cheap
                return 1.0
        else:  # "Profit"
            if price_zone == "expensive":
                return 0.1
            elif price_zone == "normal":
                return 0.4
            else:  # cheap
                return 0.8
    
    def compute_L_noncrit_effective_kw(self, price_zone: str) -> float:
        """
        Calculate effective non-critical load after applying mode/price scaling
        
        Args:
            price_zone: "cheap", "normal", or "expensive"
        
        Returns:
            Effective non-critical load in kW
        """
        alpha = self.apply_mode_and_price(price_zone)
        return alpha * self.compute_L_noncrit_kw()
    
    def compute_L_total_kw(self, price_zone: str) -> float:
        """
        Calculate total load (critical + effective non-critical)
        
        Args:
            price_zone: "cheap", "normal", or "expensive"
        
        Returns:
            Total load in kW
        """
        return self.compute_L_crit_kw() + self.compute_L_noncrit_effective_kw(price_zone)
    
    def add_device(self, device: Device):
        """Add a device to the house"""
        self.devices.append(device)
    
    def remove_device(self, device_id: int):
        """Remove a device by ID"""
        self.devices = [d for d in self.devices if d.id != device_id]
    
    def get_device(self, device_id: int) -> Optional[Device]:
        """Get device by ID"""
        for device in self.devices:
            if device.id == device_id:
                return device
        return None
    
    def set_mode(self, mode: str):
        """Set operating mode"""
        if mode in ["Eco", "Profit"]:
            self.mode = mode
        else:
            raise ValueError(f"Invalid mode: {mode}. Must be 'Eco' or 'Profit'")
    
    def get_trading_price(self, grid_price: float) -> float:
        """
        Calculate trading price based on settings.
        
        Args:
            grid_price: Current grid price in lei/kWh
        
        Returns:
            Trading price in lei/kWh
        """
        if self.trading_price_mode == "fixed" and self.trading_fixed_price is not None:
            return self.trading_fixed_price
        else:
            return grid_price * (1 - self.trading_discount_percent / 100)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "mode": self.mode,
            "has_pv": self.has_pv,
            "pv_capacity_kw": self.pv_capacity_kw,
            "has_battery": self.battery is not None,
            "battery": self.battery.to_dict() if self.battery else None,
            "devices": [d.to_dict() for d in self.devices],
            "device_count": len(self.devices),
            "L_crit_kw": round(self.compute_L_crit_kw(), 3),
            "L_noncrit_kw": round(self.compute_L_noncrit_kw(), 3),
            "trading": {
                "selling_enabled": self.selling_enabled,
                "buying_enabled": self.buying_enabled,
                "price_mode": self.trading_price_mode,
                "fixed_price_lei_kwh": self.trading_fixed_price,
                "discount_percent": self.trading_discount_percent
            }
        }
    
    def __repr__(self):
        battery_str = f", Battery: {self.battery}" if self.battery else ", No Battery"
        return f"House(ID: {self.id}, Mode: {self.mode}, Devices: {len(self.devices)}{battery_str})"
