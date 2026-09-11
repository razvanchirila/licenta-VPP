"""Energy Meter Service - calculates and tracks device energy consumption."""
import time
from typing import Dict, List, Optional
from app.models.device import Device


class EnergyMeter:
    """
    Service for calculating and managing device energy consumption.
    
    Implements event-driven metering:
    - Records timestamp when device turns ON
    - Calculates energy when device turns OFF
    - Provides real-time consumption queries
    """
    
    @staticmethod
    def on_device_toggle(device: Device) -> float:
        """
        Handle device toggle event and calculate energy.
        
        Args:
            device: The device being toggled
            
        Returns:
            Energy calculated in kWh (0 if turning ON)
        """
        return device.toggle()
    
    @staticmethod
    def get_current_consumption(device: Device) -> Dict:
        """
        Get current consumption data for a device.
        
        Args:
            device: The device to query
            
        Returns:
            Dict with accumulated_kwh, pending_kwh, total_kwh, current_power_kw
        """
        pending = device.calculate_pending_energy()
        accumulated = device.accumulated_energy_kwh
        
        return {
            "accumulated_kwh": round(accumulated, 6),
            "pending_kwh": round(pending, 6),
            "total_kwh": round(accumulated + pending, 6),
            "current_power_kw": device.get_power_kw()
        }
    
    @staticmethod
    def update_all_active_devices(devices: List[Device], dt_h: float) -> float:
        """
        Update consumption for all ON devices based on elapsed time.
        Used by simulation step.
        
        Args:
            devices: List of devices to update
            dt_h: Elapsed time in hours
            
        Returns:
            Total energy consumed by all devices in kWh
        """
        total_energy = 0.0
        
        for device in devices:
            if device.status_on:
                energy = device.get_power_kw() * dt_h
                device.accumulated_energy_kwh += energy
                total_energy += energy
        
        return total_energy
    
    @staticmethod
    def calculate_house_consumption(devices: List[Device]) -> Dict:
        """
        Calculate total consumption for a house.
        
        Args:
            devices: List of devices in the house
            
        Returns:
            Dict with total consumption data
        """
        total_accumulated = sum(d.accumulated_energy_kwh for d in devices)
        total_pending = sum(d.calculate_pending_energy() for d in devices)
        current_power = sum(d.get_power_kw() for d in devices)
        
        return {
            "total_accumulated_kwh": round(total_accumulated, 4),
            "total_pending_kwh": round(total_pending, 4),
            "total_kwh": round(total_accumulated + total_pending, 4),
            "current_power_kw": round(current_power, 3),
            "device_count": len(devices),
            "active_devices": sum(1 for d in devices if d.status_on)
        }
