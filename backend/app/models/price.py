"""
Price domain models for OPCOM energy prices.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PricePoint:
    """A single price point with timestamp."""
    timestamp: datetime
    price_lei_mwh: float
    price_lei_kwh: float
    hour: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "price_lei_mwh": round(self.price_lei_mwh, 2),
            "price_lei_kwh": round(self.price_lei_kwh, 4),
            "hour": self.hour
        }
    
    @classmethod
    def from_db_model(cls, model) -> 'PricePoint':
        """Create from database model."""
        from datetime import datetime
        # Handle both datetime and date objects
        if hasattr(model.date, 'replace'):
            try:
                timestamp = model.date.replace(hour=model.hour, minute=0, second=0, microsecond=0)
            except TypeError:
                # If model.date is a date (not datetime), convert it
                timestamp = datetime.combine(model.date, datetime.min.time()).replace(hour=model.hour)
        else:
            timestamp = datetime.combine(model.date, datetime.min.time()).replace(hour=model.hour)
        
        return cls(
            timestamp=timestamp,
            price_lei_mwh=model.price_lei_mwh,
            price_lei_kwh=model.price_lei_kwh,
            hour=model.hour
        )


@dataclass
class PriceStats:
    """Statistics for a set of prices."""
    min_price_lei_mwh: float = 0.0
    max_price_lei_mwh: float = 0.0
    avg_price_lei_mwh: float = 0.0
    min_price_lei_kwh: float = 0.0
    max_price_lei_kwh: float = 0.0
    avg_price_lei_kwh: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "min_lei_mwh": round(self.min_price_lei_mwh, 2),
            "max_lei_mwh": round(self.max_price_lei_mwh, 2),
            "avg_lei_mwh": round(self.avg_price_lei_mwh, 2),
            "min_lei_kwh": round(self.min_price_lei_kwh, 4),
            "max_lei_kwh": round(self.max_price_lei_kwh, 4),
            "avg_lei_kwh": round(self.avg_price_lei_kwh, 4)
        }
    
    @classmethod
    def from_prices(cls, prices_lei_mwh: List[float]) -> 'PriceStats':
        """Calculate statistics from a list of prices."""
        if not prices_lei_mwh:
            return cls()
        
        min_mwh = min(prices_lei_mwh)
        max_mwh = max(prices_lei_mwh)
        avg_mwh = sum(prices_lei_mwh) / len(prices_lei_mwh)
        
        return cls(
            min_price_lei_mwh=min_mwh,
            max_price_lei_mwh=max_mwh,
            avg_price_lei_mwh=avg_mwh,
            min_price_lei_kwh=min_mwh / 1000,
            max_price_lei_kwh=max_mwh / 1000,
            avg_price_lei_kwh=avg_mwh / 1000
        )


@dataclass
class PriceChange:
    """Price change information."""
    absolute_lei_mwh: float = 0.0
    percent: float = 0.0
    direction: str = "unchanged"  # "up", "down", "unchanged"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "absolute_lei_mwh": round(self.absolute_lei_mwh, 2),
            "absolute_lei_kwh": round(self.absolute_lei_mwh / 1000, 4),
            "percent": round(self.percent, 2),
            "direction": self.direction
        }
    
    @classmethod
    def calculate(cls, current: float, previous: float) -> 'PriceChange':
        """Calculate price change between two values."""
        if previous == 0:
            return cls(absolute_lei_mwh=0, percent=0, direction="unchanged")
        
        absolute = current - previous
        percent = (absolute / previous) * 100
        
        if absolute > 0:
            direction = "up"
        elif absolute < 0:
            direction = "down"
        else:
            direction = "unchanged"
        
        return cls(
            absolute_lei_mwh=absolute,
            percent=percent,
            direction=direction
        )


@dataclass
class PriceData:
    """Complete price data for a period."""
    date: str
    period: str  # "1Z", "1S", "1L", "6L", "1A"
    prices: List[PricePoint] = field(default_factory=list)
    statistics: PriceStats = field(default_factory=PriceStats)
    change: PriceChange = field(default_factory=PriceChange)
    current_price_lei_mwh: float = 0.0
    current_hour: int = 0
    source: str = "Generated"  # "OPCOM", "Cache", "Generated"
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "date": self.date,
            "period": self.period,
            "prices": [p.to_dict() for p in self.prices],
            "statistics": self.statistics.to_dict(),
            "change": self.change.to_dict(),
            "current_price_lei_mwh": round(self.current_price_lei_mwh, 2),
            "current_price_lei_kwh": round(self.current_price_lei_mwh / 1000, 4),
            "current_hour": self.current_hour,
            "source": self.source,
            "data_points": len(self.prices)
        }


@dataclass 
class DailyAverage:
    """Daily average price for historical data."""
    date: str
    avg_price_lei_mwh: float
    avg_price_lei_kwh: float
    min_price_lei_mwh: float = 0.0
    max_price_lei_mwh: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "date": self.date,
            "avg_price_lei_mwh": round(self.avg_price_lei_mwh, 2),
            "avg_price_lei_kwh": round(self.avg_price_lei_kwh, 4),
            "min_price_lei_mwh": round(self.min_price_lei_mwh, 2),
            "max_price_lei_mwh": round(self.max_price_lei_mwh, 2)
        }
