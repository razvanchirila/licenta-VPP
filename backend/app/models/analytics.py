"""Data models for energy analytics and statistics."""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class TimePeriod(Enum):
    """Time period for aggregation."""
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


@dataclass
class DeviceConsumption:
    """Energy consumption data for a single device."""
    device_id: int
    device_name: str
    total_kwh: float
    percentage_of_total: float
    estimated_cost: float


@dataclass
class ConsumptionSummary:
    """Summary of energy consumption for a period."""
    total_kwh: float
    average_daily_kwh: float
    previous_period_kwh: float
    change_percent: Optional[float]
    period: str
    estimated_cost: float
    currency: str = "RON"
    has_data: bool = True


@dataclass
class ChartDataPoint:
    """Single data point for consumption charts."""
    timestamp: datetime
    value_kwh: float


@dataclass
class MonthlyComparison:
    """Comparison between current and previous month."""
    current_month: str
    current_month_kwh: float
    previous_month: str
    previous_month_kwh: float
    change_percent: Optional[float]
    trend: str  # "increased", "decreased", "unchanged"
    projected_total_kwh: float
    is_projection: bool
    days_remaining: int


@dataclass
class CostEstimate:
    """Estimated cost for energy consumption."""
    total_cost: float
    price_per_kwh: float
    currency: str
    consumption_kwh: float
