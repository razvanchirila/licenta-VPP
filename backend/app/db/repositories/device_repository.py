"""Repository for Device CRUD operations with bulk update support."""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import DeviceModel
from .base import BaseRepository


class DeviceRepository(BaseRepository[DeviceModel]):
    """Repository for Device database operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(DeviceModel, session)
    
    async def get_by_house_id(self, house_id: int) -> List[DeviceModel]:
        """Get all devices for a specific house."""
        result = await self.session.execute(
            select(DeviceModel).where(DeviceModel.house_id == house_id)
        )
        return list(result.scalars().all())
    
    async def get_active_devices(self) -> List[DeviceModel]:
        """Get all devices that are currently ON."""
        result = await self.session.execute(
            select(DeviceModel).where(DeviceModel.status_on == True)
        )
        return list(result.scalars().all())
    
    async def get_active_devices_by_house(self, house_id: int) -> List[DeviceModel]:
        """Get all ON devices for a specific house."""
        result = await self.session.execute(
            select(DeviceModel)
            .where(DeviceModel.house_id == house_id)
            .where(DeviceModel.status_on == True)
        )
        return list(result.scalars().all())
    
    async def update_status(
        self, 
        device_id: int, 
        status_on: bool,
        last_state_change_ts: float
    ) -> Optional[DeviceModel]:
        """Update device status and timestamp."""
        device = await self.get_by_id(device_id)
        if device:
            device.status_on = status_on
            device.last_state_change_ts = last_state_change_ts
            await self.session.flush()
            await self.session.refresh(device)
        return device


    async def update_energy(
        self,
        device_id: int,
        accumulated_energy_kwh: float
    ) -> Optional[DeviceModel]:
        """Update device energy metering fields."""
        device = await self.get_by_id(device_id)
        if device:
            device.accumulated_energy_kwh = accumulated_energy_kwh
            await self.session.flush()
            await self.session.refresh(device)
        return device
    
    async def bulk_update(self, updates: List[Dict[str, Any]]) -> int:
        """
        Bulk update multiple devices in a single transaction.
        
        Args:
            updates: List of dicts with 'id' and fields to update
                    e.g., [{'id': 1, 'accumulated_energy_kwh': 5.0}, ...]
        
        Returns:
            Number of devices updated
        """
        count = 0
        for update_data in updates:
            device_id = update_data.pop('id')
            if update_data:  # Only update if there are fields to update
                await self.session.execute(
                    update(DeviceModel)
                    .where(DeviceModel.id == device_id)
                    .values(**update_data)
                )
                count += 1
        
        await self.session.flush()
        return count
    
    async def bulk_update_energy(
        self, 
        device_updates: List[Dict[str, Any]]
    ) -> int:
        """
        Bulk update energy fields for multiple devices.
        
        Args:
            device_updates: List of dicts with device_id and energy fields
                           e.g., [{'id': 1, 'accumulated_energy_kwh': 5.0}, ...]
        
        Returns:
            Number of devices updated
        """
        return await self.bulk_update(device_updates)
