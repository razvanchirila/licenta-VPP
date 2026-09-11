"""
Trading domain models for P2P energy trading
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TradingPreferences:
    """
    Trading preferences for a house in P2P energy trading.
    
    Attributes:
        house_id: House identifier
        selling_enabled: Whether house can sell to neighbors
        buying_enabled: Whether house can buy from neighbors
        price_mode: "fixed" or "discount"
        fixed_price_lei_kwh: Fixed price when price_mode="fixed"
        discount_percent: Discount from grid price when price_mode="discount"
        min_sell_price_lei_kwh: Minimum price to sell at
    """
    house_id: int
    selling_enabled: bool = True
    buying_enabled: bool = True
    price_mode: str = "discount"  # "fixed" or "discount"
    fixed_price_lei_kwh: Optional[float] = None
    discount_percent: float = 20.0
    min_sell_price_lei_kwh: float = 0.0
    
    def get_selling_price(self, grid_price: float) -> float:
        """
        Calculate actual selling price based on mode.
        
        Args:
            grid_price: Current grid price in lei/kWh
        
        Returns:
            Selling price in lei/kWh
        """
        if self.price_mode == "fixed" and self.fixed_price_lei_kwh is not None:
            price = self.fixed_price_lei_kwh
        else:
            # Discount mode: grid_price * (1 - discount_percent/100)
            price = grid_price * (1 - self.discount_percent / 100)
        
        # Ensure minimum price
        return max(price, self.min_sell_price_lei_kwh)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "house_id": self.house_id,
            "selling_enabled": self.selling_enabled,
            "buying_enabled": self.buying_enabled,
            "price_mode": self.price_mode,
            "fixed_price_lei_kwh": self.fixed_price_lei_kwh,
            "discount_percent": self.discount_percent,
            "min_sell_price_lei_kwh": self.min_sell_price_lei_kwh
        }
    
    @classmethod
    def from_db_model(cls, model) -> 'TradingPreferences':
        """Create from database model."""
        return cls(
            house_id=model.house_id,
            selling_enabled=model.selling_enabled,
            buying_enabled=model.buying_enabled,
            price_mode=model.price_mode,
            fixed_price_lei_kwh=model.fixed_price_lei_kwh,
            discount_percent=model.discount_percent,
            min_sell_price_lei_kwh=model.min_sell_price_lei_kwh
        )


@dataclass
class TradeTransaction:
    """
    A completed P2P trade transaction between two houses.
    
    Attributes:
        id: Transaction ID (None if not yet saved)
        seller_house_id: House that sold energy
        buyer_house_id: House that bought energy
        energy_kwh: Amount of energy traded
        price_lei_kwh: Price per kWh
        total_value_lei: Total transaction value
        grid_price_lei_kwh: Grid price at time of trade
        sim_timestamp: Simulation timestamp
        created_at: Real timestamp when record was created
    """
    seller_house_id: int
    buyer_house_id: int
    energy_kwh: float
    price_lei_kwh: float
    total_value_lei: float
    grid_price_lei_kwh: float
    sim_timestamp: datetime
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self, perspective_house_id: Optional[int] = None) -> dict:
        """
        Convert to dictionary for API responses.
        
        Args:
            perspective_house_id: If provided, shows transaction from this house's perspective
        """
        base = {
            "id": self.id,
            "seller_house_id": self.seller_house_id,
            "buyer_house_id": self.buyer_house_id,
            "energy_kwh": round(self.energy_kwh, 4),
            "price_lei_kwh": round(self.price_lei_kwh, 4),
            "total_value_lei": round(self.total_value_lei, 4),
            "grid_price_lei_kwh": round(self.grid_price_lei_kwh, 4),
            "sim_timestamp": self.sim_timestamp.isoformat() if self.sim_timestamp else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        
        if perspective_house_id:
            if perspective_house_id == self.seller_house_id:
                base["transaction_type"] = "sell"
                base["counterparty_house_id"] = self.buyer_house_id
            elif perspective_house_id == self.buyer_house_id:
                base["transaction_type"] = "buy"
                base["counterparty_house_id"] = self.seller_house_id
        
        return base
    
    @classmethod
    def from_db_model(cls, model) -> 'TradeTransaction':
        """Create from database model."""
        return cls(
            id=model.id,
            seller_house_id=model.seller_house_id,
            buyer_house_id=model.buyer_house_id,
            energy_kwh=model.energy_kwh,
            price_lei_kwh=model.price_lei_kwh,
            total_value_lei=model.total_value_lei,
            grid_price_lei_kwh=model.grid_price_lei_kwh,
            sim_timestamp=model.sim_timestamp,
            created_at=model.created_at
        )


@dataclass
class TradingStats:
    """Aggregated trading statistics for a house."""
    house_id: int
    total_energy_sold_kwh: float = 0.0
    total_energy_bought_kwh: float = 0.0
    total_earned_lei: float = 0.0
    total_spent_lei: float = 0.0
    net_earnings_lei: float = 0.0
    avg_sell_price_lei_kwh: float = 0.0
    avg_buy_price_lei_kwh: float = 0.0
    sell_count: int = 0
    buy_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "house_id": self.house_id,
            "total_energy_sold_kwh": round(self.total_energy_sold_kwh, 4),
            "total_energy_bought_kwh": round(self.total_energy_bought_kwh, 4),
            "total_earned_lei": round(self.total_earned_lei, 2),
            "total_spent_lei": round(self.total_spent_lei, 2),
            "net_earnings_lei": round(self.net_earnings_lei, 2),
            "avg_sell_price_lei_kwh": round(self.avg_sell_price_lei_kwh, 4),
            "avg_buy_price_lei_kwh": round(self.avg_buy_price_lei_kwh, 4),
            "sell_count": self.sell_count,
            "buy_count": self.buy_count,
            "total_trade_count": self.sell_count + self.buy_count
        }
