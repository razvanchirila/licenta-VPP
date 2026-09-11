"""Repository for House CRUD operations."""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import HouseModel, BatteryModel
from .base import BaseRepository


class HouseRepository(BaseRepository[HouseModel]):
    """Repository for House database operations."""
    
    def __init__(self, session: AsyncSession):
        super().__init__(HouseModel, session)
    
    async def get_by_id_with_relations(self, house_id: int) -> Optional[HouseModel]:
        """Get house with battery, devices, and trading data loaded."""
        result = await self.session.execute(
            select(HouseModel)
            .options(
                selectinload(HouseModel.battery),
                selectinload(HouseModel.devices),
                selectinload(HouseModel.trading_preferences),
                selectinload(HouseModel.wallet),
                selectinload(HouseModel.vpp_reserve)
            )
            .where(HouseModel.id == house_id)
        )
        return result.scalar_one_or_none()
    
    async def get_all_with_relations(self) -> List[HouseModel]:
        """Get all houses with batteries, devices, and trading data loaded."""
        result = await self.session.execute(
            select(HouseModel)
            .options(
                selectinload(HouseModel.battery),
                selectinload(HouseModel.devices),
                selectinload(HouseModel.trading_preferences),
                selectinload(HouseModel.wallet),
                selectinload(HouseModel.vpp_reserve)
            )
        )
        return list(result.scalars().all())
    
    async def update_mode(self, house_id: int, mode: str) -> Optional[HouseModel]:
        """Update house operating mode."""
        house = await self.get_by_id(house_id)
        if house:
            house.mode = mode
            await self.session.flush()
            await self.session.refresh(house)
        return house
    
    async def create_with_battery(
        self, 
        house: HouseModel, 
        battery: Optional[BatteryModel] = None
    ) -> HouseModel:
        """Create house with optional battery."""
        self.session.add(house)
        await self.session.flush()
        
        if battery:
            battery.house_id = house.id
            self.session.add(battery)
            await self.session.flush()
        
        await self.session.refresh(house)
        return house
