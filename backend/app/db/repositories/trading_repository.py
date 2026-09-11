"""Repository for trading preferences operations."""
from typing import Optional, List
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TradingPreferencesModel
from app.models.trading import TradingPreferences


class TradingPreferencesRepository:
    """Repository for trading preferences CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_house_id(self, house_id: int) -> Optional[TradingPreferences]:
        """Get trading preferences for a house."""
        result = await self.session.execute(
            select(TradingPreferencesModel).where(
                TradingPreferencesModel.house_id == house_id
            )
        )
        model = result.scalar_one_or_none()
        if model:
            return TradingPreferences.from_db_model(model)
        return None
    
    async def get_all(self) -> List[TradingPreferences]:
        """Get all trading preferences."""
        result = await self.session.execute(
            select(TradingPreferencesModel)
        )
        models = result.scalars().all()
        return [TradingPreferences.from_db_model(m) for m in models]
    
    async def get_sellers_enabled(self) -> List[TradingPreferences]:
        """Get all houses with selling enabled."""
        result = await self.session.execute(
            select(TradingPreferencesModel).where(
                TradingPreferencesModel.selling_enabled == True
            )
        )
        models = result.scalars().all()
        return [TradingPreferences.from_db_model(m) for m in models]
    
    async def get_buyers_enabled(self) -> List[TradingPreferences]:
        """Get all houses with buying enabled."""
        result = await self.session.execute(
            select(TradingPreferencesModel).where(
                TradingPreferencesModel.buying_enabled == True
            )
        )
        models = result.scalars().all()
        return [TradingPreferences.from_db_model(m) for m in models]
    
    async def update(self, house_id: int, updates: dict) -> Optional[TradingPreferences]:
        """
        Update trading preferences for a house.
        
        Args:
            house_id: House ID
            updates: Dictionary of fields to update
        
        Returns:
            Updated TradingPreferences or None if not found
        """
        # Filter out None values and invalid fields
        valid_fields = {
            'selling_enabled', 'buying_enabled', 'price_mode',
            'fixed_price_lei_kwh', 'discount_percent', 'min_sell_price_lei_kwh'
        }
        filtered_updates = {k: v for k, v in updates.items() if k in valid_fields}
        
        if not filtered_updates:
            return await self.get_by_house_id(house_id)
        
        await self.session.execute(
            update(TradingPreferencesModel)
            .where(TradingPreferencesModel.house_id == house_id)
            .values(**filtered_updates)
        )
        await self.session.commit()
        
        return await self.get_by_house_id(house_id)
    
    async def create(self, house_id: int) -> TradingPreferences:
        """Create new trading preferences with defaults."""
        model = TradingPreferencesModel(
            house_id=house_id,
            selling_enabled=True,
            buying_enabled=True,
            price_mode="discount",
            fixed_price_lei_kwh=0.8,
            discount_percent=20.0,
            min_sell_price_lei_kwh=0.3
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return TradingPreferences.from_db_model(model)
    
    async def create_from_prefs(self, prefs: TradingPreferences) -> TradingPreferences:
        """Create new trading preferences from TradingPreferences object."""
        model = TradingPreferencesModel(
            house_id=prefs.house_id,
            selling_enabled=prefs.selling_enabled,
            buying_enabled=prefs.buying_enabled,
            price_mode=prefs.price_mode,
            fixed_price_lei_kwh=prefs.fixed_price_lei_kwh,
            discount_percent=prefs.discount_percent,
            min_sell_price_lei_kwh=prefs.min_sell_price_lei_kwh
        )
        self.session.add(model)
        await self.session.commit()
        await self.session.refresh(model)
        return TradingPreferences.from_db_model(model)
