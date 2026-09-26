"""Device statistics from energy_logs; periods are anchored to the simulated "now", not the wall clock."""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories import EnergyLogRepository

DEFAULT_PRICE_PER_KWH = 1.0   # rough retail price behind the "estimated cost" fields
CURRENCY = "RON"


class TimePeriod(Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass
class DeviceConsumption:
    device_id: int
    device_name: str
    total_kwh: float
    percentage_of_total: float
    estimated_cost: float


@dataclass
class ConsumptionSummary:
    total_kwh: float
    average_daily_kwh: float
    previous_period_kwh: float
    change_percent: float | None
    period: str
    estimated_cost: float
    currency: str = CURRENCY
    has_data: bool = True


@dataclass
class ChartDataPoint:
    timestamp: datetime
    value_kwh: float


@dataclass
class MonthlyComparison:
    current_month: str
    current_month_kwh: float
    previous_month: str
    previous_month_kwh: float
    change_percent: float | None
    trend: str
    projected_total_kwh: float
    is_projection: bool
    days_remaining: int


def _change_percent(current: float, previous: float) -> float | None:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round((current - previous) / previous * 100, 1)


class AnalyticsService:
    def __init__(self, session: AsyncSession, now: datetime):
        self.repo = EnergyLogRepository(session)
        self.now = now

    def _period_dates(self, period: TimePeriod) -> tuple[datetime, datetime]:
        now = self.now
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == TimePeriod.WEEK:
            return midnight - timedelta(days=now.weekday()), now
        if period == TimePeriod.MONTH:
            return midnight.replace(day=1), now
        if period == TimePeriod.YEAR:
            return midnight.replace(month=1, day=1), now
        return midnight, now

    def _previous_period_dates(self, period: TimePeriod) -> tuple[datetime, datetime]:
        start, _ = self._period_dates(period)
        if period == TimePeriod.WEEK:
            prev = start - timedelta(days=7)
        elif period == TimePeriod.MONTH:
            prev = (start - timedelta(days=1)).replace(day=1)
        elif period == TimePeriod.YEAR:
            prev = start.replace(year=start.year - 1)
        else:
            prev = start - timedelta(days=1)
        return prev, start - timedelta(microseconds=1)

    async def top_consumers(self, house_id: int, period: TimePeriod = TimePeriod.MONTH, limit: int = 10,
                            price_per_kwh: float = DEFAULT_PRICE_PER_KWH) -> tuple[float, list[DeviceConsumption]]:
        start, end = self._period_dates(period)
        rows = await self.repo.get_aggregated_by_device(house_id, start, end)
        total = sum(r["total_kwh"] for r in rows)
        devices = [
            DeviceConsumption(
                device_id=r["device_id"], device_name=r["device_name"], total_kwh=round(r["total_kwh"], 4),
                percentage_of_total=round(r["total_kwh"] / total * 100, 1) if total > 0 else 0.0,
                estimated_cost=round(r["total_kwh"] * price_per_kwh, 2),
            )
            for r in rows[:limit]
        ]
        return round(total, 4), devices

    async def consumption_summary(self, house_id: int, period: TimePeriod = TimePeriod.MONTH,
                                  price_per_kwh: float = DEFAULT_PRICE_PER_KWH) -> ConsumptionSummary:
        start, end = self._period_dates(period)
        prev_start, prev_end = self._previous_period_dates(period)
        current = await self.repo.get_total_for_period(house_id, start, end)
        previous = await self.repo.get_total_for_period(house_id, prev_start, prev_end)
        days = (end - start).days + 1
        return ConsumptionSummary(
            total_kwh=round(current, 4), average_daily_kwh=round(current / days, 4) if days > 0 else 0.0,
            previous_period_kwh=round(previous, 4), change_percent=_change_percent(current, previous),
            period=period.value, estimated_cost=round(current * price_per_kwh, 2),
            has_data=current > 0 or previous > 0,
        )

    async def chart_data(self, house_id: int, start_date: datetime,
                         end_date: datetime) -> tuple[str, list[ChartDataPoint]]:
        days_range = (end_date - start_date).days
        if days_range < 7:
            rows = await self.repo.get_aggregated_by_hour(house_id, start_date, end_date)
            return "hourly", [ChartDataPoint(datetime.combine(r["date"], datetime.min.time()).replace(hour=r["hour"]),
                                             r["total_kwh"]) for r in rows]
        rows = await self.repo.get_aggregated_by_day(house_id, start_date, end_date)
        if days_range <= 30:
            return "daily", [ChartDataPoint(datetime.combine(r["date"], datetime.min.time()), r["total_kwh"])
                             for r in rows]
        weekly: dict[tuple[int, int], float] = {}
        for r in rows:
            iso_year, iso_week, _ = r["date"].isocalendar()
            weekly[(iso_year, iso_week)] = weekly.get((iso_year, iso_week), 0.0) + r["total_kwh"]
        return "weekly", [ChartDataPoint(datetime.fromisocalendar(y, w, 1), v) for (y, w), v in sorted(weekly.items())]

    async def monthly_comparison(self, house_id: int) -> MonthlyComparison:
        now = self.now
        current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_end = current_start - timedelta(microseconds=1)
        prev_start = prev_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current = await self.repo.get_total_for_period(house_id, current_start, now)
        previous = await self.repo.get_total_for_period(house_id, prev_start, prev_end)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        days_remaining = days_in_month - now.day
        projected = current / now.day * days_in_month if days_remaining > 0 else current
        change = _change_percent(current, previous)
        trend = "unchanged" if not change else ("increased" if change > 0 else "decreased")
        return MonthlyComparison(
            current_month=now.strftime("%B %Y"), current_month_kwh=round(current, 4),
            previous_month=prev_end.strftime("%B %Y"), previous_month_kwh=round(previous, 4),
            change_percent=change, trend=trend, projected_total_kwh=round(projected, 4),
            is_projection=days_remaining > 0, days_remaining=days_remaining,
        )
