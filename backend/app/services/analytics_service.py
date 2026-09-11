"""Analytics Service - calculates and aggregates energy statistics."""
import calendar
import hashlib
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.energy_log_repository import EnergyLogRepository
from app.models.analytics import (
    ChartDataPoint,
    ConsumptionSummary,
    CostEstimate,
    DeviceConsumption,
    MonthlyComparison,
    TimePeriod,
)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    data: Any
    created_at: datetime
    ttl_seconds: int
    
    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        age = (datetime.now() - self.created_at).total_seconds()
        return age < self.ttl_seconds


# Global cache storage (shared across service instances)
_analytics_cache: Dict[str, CacheEntry] = {}


class AnalyticsService:
    """Service for calculating and aggregating energy statistics."""
    
    DEFAULT_PRICE_PER_KWH = 1.0  # RON per kWh
    DEFAULT_CURRENCY = "RON"
    DEFAULT_CACHE_TTL = 300  # 5 minutes
    
    def __init__(self, session: AsyncSession, cache_ttl: int = DEFAULT_CACHE_TTL):
        self.session = session
        self.repo = EnergyLogRepository(session)
        self.cache_ttl = cache_ttl
    
    def _cache_key(self, house_id: int, method: str, params: str = "") -> str:
        """Generate cache key."""
        params_hash = hashlib.md5(params.encode()).hexdigest()[:8] if params else ""
        return f"{house_id}:{method}:{params_hash}"
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if valid."""
        entry = _analytics_cache.get(key)
        if entry and entry.is_valid():
            return entry.data
        return None
    
    def _set_cached(self, key: str, data: Any) -> None:
        """Store value in cache."""
        _analytics_cache[key] = CacheEntry(
            data=data,
            created_at=datetime.now(),
            ttl_seconds=self.cache_ttl
        )
    
    def calculate_cost(
        self,
        consumption_kwh: float,
        price_per_kwh: float = DEFAULT_PRICE_PER_KWH,
        currency: str = DEFAULT_CURRENCY
    ) -> CostEstimate:
        """Calculate estimated cost for energy consumption."""
        return CostEstimate(
            total_cost=round(consumption_kwh * price_per_kwh, 2),
            price_per_kwh=price_per_kwh,
            currency=currency,
            consumption_kwh=consumption_kwh
        )
    
    def _get_period_dates(
        self, 
        period: TimePeriod, 
        reference_date: Optional[datetime] = None
    ) -> tuple[datetime, datetime]:
        """Get start and end dates for a time period."""
        now = reference_date or datetime.now()
        
        if period == TimePeriod.DAY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == TimePeriod.WEEK:
            start = now - timedelta(days=now.weekday())
            start = start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == TimePeriod.MONTH:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period == TimePeriod.YEAR:
            start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        else:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        
        return start, end
    
    def _get_previous_period_dates(
        self, 
        period: TimePeriod, 
        reference_date: Optional[datetime] = None
    ) -> tuple[datetime, datetime]:
        """Get start and end dates for the previous time period."""
        now = reference_date or datetime.now()
        
        if period == TimePeriod.DAY:
            prev_day = now - timedelta(days=1)
            start = prev_day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = prev_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == TimePeriod.WEEK:
            prev_week_start = now - timedelta(days=now.weekday() + 7)
            start = prev_week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        elif period == TimePeriod.MONTH:
            first_of_month = now.replace(day=1)
            last_month_end = first_of_month - timedelta(days=1)
            start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = last_month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif period == TimePeriod.YEAR:
            start = now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(year=now.year - 1, month=12, day=31, hour=23, minute=59, second=59)
        else:
            prev_day = now - timedelta(days=1)
            start = prev_day.replace(hour=0, minute=0, second=0, microsecond=0)
            end = prev_day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return start, end
    
    def _calculate_change_percent(
        self, 
        current: float, 
        previous: float
    ) -> Optional[float]:
        """Calculate percentage change between two values."""
        if previous == 0:
            if current > 0:
                return 100.0
            return 0.0
        return round(((current - previous) / previous) * 100, 1)
    
    async def get_top_consumers(
        self,
        house_id: int,
        period: TimePeriod = TimePeriod.MONTH,
        limit: int = 10,
        price_per_kwh: float = DEFAULT_PRICE_PER_KWH
    ) -> List[DeviceConsumption]:
        """Get top energy consuming devices for a house."""
        start_date, end_date = self._get_period_dates(period)
        
        aggregated = await self.repo.get_aggregated_by_device(
            house_id=house_id,
            start_date=start_date,
            end_date=end_date
        )
        
        if not aggregated:
            return []
        
        total_kwh = sum(d['total_kwh'] for d in aggregated)
        
        result = []
        for device in aggregated[:limit]:
            percentage = (device['total_kwh'] / total_kwh * 100) if total_kwh > 0 else 0
            result.append(DeviceConsumption(
                device_id=device['device_id'],
                device_name=device['device_name'],
                total_kwh=round(device['total_kwh'], 4),
                percentage_of_total=round(percentage, 1),
                estimated_cost=round(device['total_kwh'] * price_per_kwh, 2)
            ))
        
        return result

    
    async def get_consumption_summary(
        self,
        house_id: int,
        period: TimePeriod = TimePeriod.MONTH,
        price_per_kwh: float = DEFAULT_PRICE_PER_KWH
    ) -> ConsumptionSummary:
        """Get consumption summary for a house."""
        start_date, end_date = self._get_period_dates(period)
        prev_start, prev_end = self._get_previous_period_dates(period)
        
        current_total = await self.repo.get_total_for_period(
            house_id=house_id,
            start_date=start_date,
            end_date=end_date
        )
        
        previous_total = await self.repo.get_total_for_period(
            house_id=house_id,
            start_date=prev_start,
            end_date=prev_end
        )
        
        # Calculate days in current period
        days_elapsed = (end_date - start_date).days + 1
        average_daily = current_total / days_elapsed if days_elapsed > 0 else 0
        
        change_percent = self._calculate_change_percent(current_total, previous_total)
        
        return ConsumptionSummary(
            total_kwh=round(current_total, 4),
            average_daily_kwh=round(average_daily, 4),
            previous_period_kwh=round(previous_total, 4),
            change_percent=change_percent,
            period=period.value,
            estimated_cost=round(current_total * price_per_kwh, 2),
            currency=self.DEFAULT_CURRENCY,
            has_data=current_total > 0 or previous_total > 0
        )
    
    async def get_chart_data(
        self,
        house_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> tuple[str, List[ChartDataPoint]]:
        """
        Get chart data with adaptive granularity.
        
        Returns tuple of (granularity, data_points).
        """
        days_range = (end_date - start_date).days
        
        # Select granularity based on range
        if days_range < 7:
            granularity = "hourly"
            raw_data = await self.repo.get_aggregated_by_hour(
                house_id=house_id,
                start_date=start_date,
                end_date=end_date
            )
            data_points = [
                ChartDataPoint(
                    timestamp=datetime.combine(d['date'], datetime.min.time()).replace(hour=d['hour']),
                    value_kwh=d['total_kwh']
                )
                for d in raw_data
            ]
        elif days_range <= 30:
            granularity = "daily"
            raw_data = await self.repo.get_aggregated_by_day(
                house_id=house_id,
                start_date=start_date,
                end_date=end_date
            )
            data_points = [
                ChartDataPoint(
                    timestamp=datetime.combine(d['date'], datetime.min.time()) if hasattr(d['date'], 'year') else datetime.fromisoformat(str(d['date'])),
                    value_kwh=d['total_kwh']
                )
                for d in raw_data
            ]
        else:
            granularity = "weekly"
            # For weekly, we aggregate daily data into weeks
            raw_data = await self.repo.get_aggregated_by_day(
                house_id=house_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # Group by week
            weekly_data: Dict[int, float] = {}
            for d in raw_data:
                dt = datetime.combine(d['date'], datetime.min.time()) if hasattr(d['date'], 'year') else datetime.fromisoformat(str(d['date']))
                week_num = dt.isocalendar()[1]
                week_key = dt.year * 100 + week_num
                weekly_data[week_key] = weekly_data.get(week_key, 0) + d['total_kwh']
            
            data_points = []
            for week_key in sorted(weekly_data.keys()):
                year = week_key // 100
                week = week_key % 100
                # Get first day of week
                first_day = datetime.strptime(f'{year}-W{week:02d}-1', '%Y-W%W-%w')
                data_points.append(ChartDataPoint(
                    timestamp=first_day,
                    value_kwh=weekly_data[week_key]
                ))
        
        return granularity, data_points
    
    async def get_monthly_comparison(
        self,
        house_id: int,
        price_per_kwh: float = DEFAULT_PRICE_PER_KWH
    ) -> MonthlyComparison:
        """Get comparison between current and previous month."""
        now = datetime.now()
        
        # Current month
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_end = now
        
        # Previous month
        prev_month_end = current_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        current_total = await self.repo.get_total_for_period(
            house_id=house_id,
            start_date=current_start,
            end_date=current_end
        )
        
        previous_total = await self.repo.get_total_for_period(
            house_id=house_id,
            start_date=prev_month_start,
            end_date=prev_month_end
        )
        
        # Calculate projection if month is incomplete
        days_elapsed = now.day
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_remaining = days_in_month - days_elapsed
        
        is_projection = days_remaining > 0
        if is_projection and days_elapsed > 0:
            daily_average = current_total / days_elapsed
            projected_total = daily_average * days_in_month
        else:
            projected_total = current_total
        
        change_percent = self._calculate_change_percent(current_total, previous_total)
        
        if change_percent is None or change_percent == 0:
            trend = "unchanged"
        elif change_percent > 0:
            trend = "increased"
        else:
            trend = "decreased"
        
        return MonthlyComparison(
            current_month=now.strftime("%B %Y"),
            current_month_kwh=round(current_total, 4),
            previous_month=prev_month_end.strftime("%B %Y"),
            previous_month_kwh=round(previous_total, 4),
            change_percent=change_percent,
            trend=trend,
            projected_total_kwh=round(projected_total, 4),
            is_projection=is_projection,
            days_remaining=days_remaining
        )
