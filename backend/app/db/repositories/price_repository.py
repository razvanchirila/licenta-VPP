"""Repository for OPCOM price cache operations."""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OpcomPriceModel


class PriceRepository:
    """Repository for OPCOM price cache CRUD operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_cached_prices(self, date: datetime) -> List[OpcomPriceModel]:
        """
        Get cached prices for a specific date.
        
        Args:
            date: Date to get prices for (time part ignored)
        
        Returns:
            List of OpcomPriceModel for all 24 hours, or empty list if not cached
        """
        # Normalize to start of day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        result = await self.session.execute(
            select(OpcomPriceModel)
            .where(and_(
                OpcomPriceModel.date >= start_of_day,
                OpcomPriceModel.date < end_of_day
            ))
            .order_by(OpcomPriceModel.hour)
        )
        return list(result.scalars().all())
    
    async def save_prices(self, date: datetime, prices_lei_mwh: List[float]) -> List[OpcomPriceModel]:
        """
        Save 24 hourly prices for a date.
        
        Args:
            date: Date for the prices
            prices_lei_mwh: List of 24 prices in lei/MWh
        
        Returns:
            List of saved OpcomPriceModel
        """
        if len(prices_lei_mwh) != 24:
            raise ValueError(f"Expected 24 prices, got {len(prices_lei_mwh)}")
        
        # Normalize to start of day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Delete existing prices for this date
        await self.session.execute(
            delete(OpcomPriceModel).where(and_(
                OpcomPriceModel.date >= start_of_day,
                OpcomPriceModel.date < start_of_day + timedelta(days=1)
            ))
        )
        
        # Insert new prices
        models = []
        now = datetime.now()
        for hour, price_mwh in enumerate(prices_lei_mwh):
            model = OpcomPriceModel(
                date=start_of_day,
                hour=hour,
                price_lei_mwh=price_mwh,
                price_lei_kwh=price_mwh / 1000.0,
                fetched_at=now
            )
            self.session.add(model)
            models.append(model)
        
        await self.session.commit()
        
        # Refresh to get IDs
        for model in models:
            await self.session.refresh(model)
        
        return models
    
    async def get_daily_averages(
        self, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[dict]:
        """
        Get daily average prices for a date range.
        
        Args:
            start_date: Start of range
            end_date: End of range
        
        Returns:
            List of dicts with date and average prices
        """
        result = await self.session.execute(
            select(
                func.date(OpcomPriceModel.date).label('price_date'),
                func.avg(OpcomPriceModel.price_lei_mwh).label('avg_price_mwh'),
                func.min(OpcomPriceModel.price_lei_mwh).label('min_price_mwh'),
                func.max(OpcomPriceModel.price_lei_mwh).label('max_price_mwh')
            )
            .where(and_(
                OpcomPriceModel.date >= start_date,
                OpcomPriceModel.date <= end_date
            ))
            .group_by(func.date(OpcomPriceModel.date))
            .order_by(func.date(OpcomPriceModel.date))
        )
        
        rows = result.all()
        return [
            {
                "date": row.price_date,
                "avg_price_lei_mwh": round(row.avg_price_mwh, 2) if row.avg_price_mwh else 0,
                "avg_price_lei_kwh": round(row.avg_price_mwh / 1000, 4) if row.avg_price_mwh else 0,
                "min_price_lei_mwh": round(row.min_price_mwh, 2) if row.min_price_mwh else 0,
                "max_price_lei_mwh": round(row.max_price_mwh, 2) if row.max_price_mwh else 0
            }
            for row in rows
        ]
    
    async def is_cache_valid(self, date: datetime, max_age_hours: int = 1) -> bool:
        """
        Check if cached data for a date is still valid.
        
        Args:
            date: Date to check
            max_age_hours: Maximum age in hours for cache to be valid
        
        Returns:
            True if cache exists and is fresh, False otherwise
        """
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        result = await self.session.execute(
            select(func.count(OpcomPriceModel.id))
            .where(and_(
                OpcomPriceModel.date >= start_of_day,
                OpcomPriceModel.date < start_of_day + timedelta(days=1),
                OpcomPriceModel.fetched_at >= cutoff_time
            ))
        )
        count = result.scalar()
        
        # Valid if we have all 24 hours cached and fresh
        return count == 24
    
    async def get_price_for_hour(self, date: datetime, hour: int) -> Optional[OpcomPriceModel]:
        """Get price for a specific date and hour."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.session.execute(
            select(OpcomPriceModel)
            .where(and_(
                OpcomPriceModel.date >= start_of_day,
                OpcomPriceModel.date < start_of_day + timedelta(days=1),
                OpcomPriceModel.hour == hour
            ))
        )
        return result.scalar_one_or_none()
