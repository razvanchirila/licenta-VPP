"""Repository for VPP reserve operations."""
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import VPPReserveModel
from app.models.wallet import VPPReserve


class VPPReserveRepository:
    """Repository for VPP reserve CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_house_id(self, house_id: int) -> Optional[VPPReserve]:
        """Get VPP reserve for a house."""
        result = await self.session.execute(
            select(VPPReserveModel).where(VPPReserveModel.house_id == house_id)
        )
        model = result.scalar_one_or_none()
        if model:
            return VPPReserve.from_db_model(model)
        return None
    
    async def get_all(self) -> List[VPPReserve]:
        """Get all VPP reserves."""
        result = await self.session.execute(select(VPPReserveModel))
        models = result.scalars().all()
        return [VPPReserve.from_db_model(m) for m in models]
    
    async def get_total_reserve(self) -> float:
        """Get total VPP reserve across all houses."""
        result = await self.session.execute(select(VPPReserveModel))
        models = result.scalars().all()
        return sum(m.reserved_kwh for m in models)
    
    async def add_reserve(self, house_id: int, kwh: float) -> Optional[VPPReserve]:
        """
        Add energy to VPP reserve for a house.
        
        Args:
            house_id: House ID
            kwh: Energy to add in kWh
        
        Returns:
            Updated VPPReserve or None if not found
        """
        result = await self.session.execute(
            select(VPPReserveModel).where(VPPReserveModel.house_id == house_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        model.reserved_kwh += kwh
        await self.session.commit()
        await self.session.refresh(model)
        
        return VPPReserve.from_db_model(model)
    
    async def use_reserve(self, house_id: int, kwh: float) -> tuple[float, Optional[VPPReserve]]:
        """
        Use energy from VPP reserve.
        
        Args:
            house_id: House ID
            kwh: Energy to use in kWh
        
        Returns:
            Tuple of (actual_used_kwh, updated_reserve)
        """
        result = await self.session.execute(
            select(VPPReserveModel).where(VPPReserveModel.house_id == house_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return 0.0, None
        
        actual_used = min(kwh, model.reserved_kwh)
        model.reserved_kwh -= actual_used
        
        await self.session.commit()
        await self.session.refresh(model)
        
        return actual_used, VPPReserve.from_db_model(model)
    
    async def add_bonus(self, house_id: int, amount_lei: float) -> Optional[VPPReserve]:
        """
        Add bonus to VPP reserve for a house.
        
        Args:
            house_id: House ID
            amount_lei: Bonus amount in lei
        
        Returns:
            Updated VPPReserve or None if not found
        """
        result = await self.session.execute(
            select(VPPReserveModel).where(VPPReserveModel.house_id == house_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return None
        
        model.pending_bonus_lei += amount_lei
        await self.session.commit()
        await self.session.refresh(model)
        
        return VPPReserve.from_db_model(model)
    
    async def claim_bonus(self, house_id: int) -> tuple[float, Optional[VPPReserve]]:
        """
        Claim pending bonus from VPP reserve.
        
        Args:
            house_id: House ID
        
        Returns:
            Tuple of (bonus_amount, updated_reserve)
        """
        result = await self.session.execute(
            select(VPPReserveModel).where(VPPReserveModel.house_id == house_id)
        )
        model = result.scalar_one_or_none()
        
        if not model:
            return 0.0, None
        
        bonus = model.pending_bonus_lei
        model.pending_bonus_lei = 0.0
        
        await self.session.commit()
        await self.session.refresh(model)
        
        return bonus, VPPReserve.from_db_model(model)
    
    async def update_base_rate(self, house_id: int, rate: float) -> Optional[VPPReserve]:
        """Update base rate for a house's VPP reserve."""
        await self.session.execute(
            update(VPPReserveModel)
            .where(VPPReserveModel.house_id == house_id)
            .values(base_rate_lei_kwh=rate)
        )
        await self.session.commit()
        return await self.get_by_house_id(house_id)
