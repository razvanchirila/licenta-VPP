"""
Price Service for OPCOM energy prices.

Provides high-level operations for fetching, caching, and analyzing OPCOM prices.
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.price_repository import PriceRepository
from app.models.price import PriceData, PricePoint, PriceStats, PriceChange, DailyAverage


class PriceService:
    """Service for managing OPCOM price operations."""
    
    # Period to days mapping
    PERIOD_DAYS = {
        "1Z": 1,    # 1 day (24 hourly points)
        "1S": 7,    # 1 week (7 daily averages)
        "1L": 30,   # 1 month (30 daily averages)
        "6L": 180,  # 6 months
        "1A": 365   # 1 year
    }
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = PriceRepository(session)
    
    async def get_prices_for_period(
        self, 
        period: str = "1Z", 
        date: datetime = None
    ) -> PriceData:
        """
        Get prices for a specified period.
        
        Args:
            period: Period code ("1Z", "1S", "1L", "6L", "1A")
            date: Reference date (default: today)
        
        Returns:
            PriceData with prices and statistics
        """
        if date is None:
            date = datetime.now()
        
        if period == "1Z":
            # Daily: 24 hourly prices
            return await self._get_daily_prices(date)
        else:
            # Weekly/Monthly/etc: daily averages
            days = self.PERIOD_DAYS.get(period, 7)
            return await self._get_historical_prices(date, days, period)
    
    async def _get_daily_prices(self, date: datetime) -> PriceData:
        """Get 24 hourly prices for a specific day."""
        current_hour = datetime.now().hour
        
        # Check cache first
        if await self.repo.is_cache_valid(date, max_age_hours=1):
            cached = await self.repo.get_cached_prices(date)
            if len(cached) == 24:
                prices = [PricePoint.from_db_model(m) for m in cached]
                return self._build_price_data(prices, date, "1Z", "Cache", current_hour)
        
        # Fetch from OPCOM
        try:
            from app.sim.opcom import fetch_opcom_prices_raw
            opcom_data = fetch_opcom_prices_raw(date)
            
            # Save to cache
            await self.repo.save_prices(date, opcom_data["prices_lei_mwh"])
            
            # Build price points
            prices = []
            for hour, price_mwh in enumerate(opcom_data["prices_lei_mwh"]):
                prices.append(PricePoint(
                    timestamp=date.replace(hour=hour, minute=0, second=0, microsecond=0),
                    price_lei_mwh=price_mwh,
                    price_lei_kwh=price_mwh / 1000,
                    hour=hour
                ))
            
            return self._build_price_data(prices, date, "1Z", "OPCOM", current_hour)
            
        except Exception as e:
            print(f"Failed to fetch OPCOM prices: {e}")
            # Try to return stale cache
            cached = await self.repo.get_cached_prices(date)
            if cached:
                prices = [PricePoint.from_db_model(m) for m in cached]
                return self._build_price_data(prices, date, "1Z", "Cache (stale)", current_hour)
            
            # Generate fallback prices
            return self._generate_fallback_prices(date, "1Z", current_hour)
    
    async def _get_historical_prices(
        self, 
        end_date: datetime, 
        days: int,
        period: str
    ) -> PriceData:
        """Get daily average prices for historical period."""
        start_date = end_date - timedelta(days=days)
        current_hour = datetime.now().hour
        
        # Get daily averages from cache
        averages = await self.repo.get_daily_averages(start_date, end_date)
        
        if len(averages) >= days * 0.8:  # At least 80% of days have data
            prices = []
            for avg in averages:
                date_obj = avg["date"] if isinstance(avg["date"], datetime) else datetime.strptime(str(avg["date"]), "%Y-%m-%d")
                prices.append(PricePoint(
                    timestamp=date_obj,
                    price_lei_mwh=avg["avg_price_lei_mwh"],
                    price_lei_kwh=avg["avg_price_lei_kwh"],
                    hour=12  # Midday for daily averages
                ))
            
            return self._build_price_data(prices, end_date, period, "Cache", current_hour)
        
        # Not enough cached data - generate fallback
        return self._generate_fallback_prices(end_date, period, current_hour, days)
    
    def _build_price_data(
        self, 
        prices: List[PricePoint], 
        date: datetime, 
        period: str,
        source: str,
        current_hour: int
    ) -> PriceData:
        """Build PriceData from price points."""
        if not prices:
            return PriceData(
                date=date.strftime("%d/%m/%Y"),
                period=period,
                source=source,
                current_hour=current_hour
            )
        
        prices_mwh = [p.price_lei_mwh for p in prices]
        stats = PriceStats.from_prices(prices_mwh)
        
        # Current price (last price or price at current hour)
        if period == "1Z" and current_hour < len(prices):
            current_price = prices[current_hour].price_lei_mwh
            # Calculate change from previous hour
            prev_hour = (current_hour - 1) % 24
            prev_price = prices[prev_hour].price_lei_mwh if prev_hour < len(prices) else current_price
        else:
            current_price = prices[-1].price_lei_mwh
            prev_price = prices[-2].price_lei_mwh if len(prices) > 1 else current_price
        
        change = PriceChange.calculate(current_price, prev_price)
        
        return PriceData(
            date=date.strftime("%d/%m/%Y"),
            period=period,
            prices=prices,
            statistics=stats,
            change=change,
            current_price_lei_mwh=current_price,
            current_hour=current_hour,
            source=source
        )
    
    def _generate_fallback_prices(
        self, 
        date: datetime, 
        period: str, 
        current_hour: int,
        days: int = 1
    ) -> PriceData:
        """Generate synthetic fallback prices when OPCOM is unavailable."""
        import random
        import math
        
        prices = []
        
        if period == "1Z":
            # Generate 24 hourly prices with realistic pattern
            base_price = 450  # Base price in lei/MWh
            for hour in range(24):
                # Price pattern: lower at night, higher during day
                hour_factor = 1 + 0.3 * math.sin((hour - 6) * math.pi / 12)
                noise = random.uniform(-30, 30)
                price_mwh = base_price * hour_factor + noise
                
                prices.append(PricePoint(
                    timestamp=date.replace(hour=hour, minute=0, second=0, microsecond=0),
                    price_lei_mwh=price_mwh,
                    price_lei_kwh=price_mwh / 1000,
                    hour=hour
                ))
        else:
            # Generate daily averages
            base_price = 450
            for i in range(days):
                day = date - timedelta(days=days - i - 1)
                noise = random.uniform(-50, 50)
                price_mwh = base_price + noise
                
                prices.append(PricePoint(
                    timestamp=day,
                    price_lei_mwh=price_mwh,
                    price_lei_kwh=price_mwh / 1000,
                    hour=12
                ))
        
        return self._build_price_data(prices, date, period, "Generated", current_hour)
    
    async def get_current_price(self) -> dict:
        """Get current hour's OPCOM price."""
        now = datetime.now()
        current_hour = now.hour
        
        # Try cache first
        cached = await self.repo.get_price_for_hour(now, current_hour)
        if cached:
            return {
                "price_lei_mwh": cached.price_lei_mwh,
                "price_lei_kwh": cached.price_lei_kwh,
                "hour": current_hour,
                "date": now.strftime("%d/%m/%Y"),
                "source": "Cache"
            }
        
        # Fetch from OPCOM
        try:
            from app.sim.opcom import fetch_opcom_prices
            prices = fetch_opcom_prices(now)
            
            # Save to cache
            from app.sim.opcom import fetch_opcom_prices_raw
            opcom_data = fetch_opcom_prices_raw(now)
            await self.repo.save_prices(now, opcom_data["prices_lei_mwh"])
            
            return {
                "price_lei_mwh": opcom_data["prices_lei_mwh"][current_hour],
                "price_lei_kwh": prices[current_hour],
                "hour": current_hour,
                "date": now.strftime("%d/%m/%Y"),
                "source": "OPCOM"
            }
        except Exception as e:
            # Fallback
            return {
                "price_lei_mwh": 450.0,
                "price_lei_kwh": 0.45,
                "hour": current_hour,
                "date": now.strftime("%d/%m/%Y"),
                "source": "Generated",
                "error": str(e)
            }
    
    async def refresh_cache_if_needed(self, date: datetime = None) -> bool:
        """
        Refresh cache if data is stale.
        
        Returns:
            True if cache was refreshed, False if already fresh
        """
        if date is None:
            date = datetime.now()
        
        if await self.repo.is_cache_valid(date, max_age_hours=1):
            return False
        
        try:
            from app.sim.opcom import fetch_opcom_prices_raw
            opcom_data = fetch_opcom_prices_raw(date)
            await self.repo.save_prices(date, opcom_data["prices_lei_mwh"])
            return True
        except Exception:
            return False
