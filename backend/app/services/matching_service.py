"""
Matching Service for P2P energy trading.

Implements the algorithm to match sellers with buyers optimally:
1. Sort sellers by price ascending (cheapest first)
2. Sort buyers by deficit descending (highest need first)
3. Match while respecting line limits and price constraints
"""
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from app.models.trading import TradingPreferences, TradeTransaction


@dataclass
class SellerOffer:
    """A seller's offer to sell energy."""
    house_id: int
    surplus_kwh: float
    price_lei_kwh: float
    preferences: TradingPreferences


@dataclass
class BuyerRequest:
    """A buyer's request to buy energy."""
    house_id: int
    deficit_kwh: float
    preferences: TradingPreferences


@dataclass
class TradeMatch:
    """A matched trade between seller and buyer."""
    seller_house_id: int
    buyer_house_id: int
    energy_kwh: float
    price_lei_kwh: float
    total_value_lei: float


class MatchingService:
    """
    Service for matching P2P energy trades.
    
    Algorithm:
    1. Filter sellers with selling_enabled=True
    2. Filter buyers with buying_enabled=True
    3. Sort sellers by price ascending (cheapest first)
    4. Sort buyers by deficit descending (highest need first)
    5. For each buyer, find cheapest available seller
    6. Execute trade if seller price < grid price
    7. Respect internal line limit
    """
    
    def __init__(self, line_limit_kw: float = 1000.0):
        """
        Initialize matching service.
        
        Args:
            line_limit_kw: Maximum power on internal network (kW)
        """
        self.line_limit_kw = line_limit_kw
    
    def match_trades(
        self,
        sellers: List[SellerOffer],
        buyers: List[BuyerRequest],
        grid_price: float,
        dt_hours: float = 1.0
    ) -> List[TradeMatch]:
        """
        Match sellers to buyers optimally.
        
        Args:
            sellers: List of seller offers
            buyers: List of buyer requests
            grid_price: Current grid price in lei/kWh
            dt_hours: Time step duration in hours
        
        Returns:
            List of matched trades
        """
        if not sellers or not buyers:
            return []
        
        # Filter only enabled participants
        active_sellers = [s for s in sellers if s.preferences.selling_enabled and s.surplus_kwh > 0]
        active_buyers = [b for b in buyers if b.preferences.buying_enabled and b.deficit_kwh > 0]
        
        if not active_sellers or not active_buyers:
            return []
        
        # Sort sellers by price ascending (cheapest first)
        active_sellers.sort(key=lambda s: s.price_lei_kwh)
        
        # Sort buyers by deficit descending (highest need first)
        active_buyers.sort(key=lambda b: b.deficit_kwh, reverse=True)
        
        trades = []
        total_traded_kwh = 0.0
        max_trade_kwh = self.line_limit_kw * dt_hours  # Convert power limit to energy limit
        
        # Track remaining surplus/deficit
        seller_remaining = {s.house_id: s.surplus_kwh for s in active_sellers}
        buyer_remaining = {b.house_id: b.deficit_kwh for b in active_buyers}
        
        # Match buyers to sellers
        for buyer in active_buyers:
            if buyer_remaining[buyer.house_id] <= 0:
                continue
            
            for seller in active_sellers:
                if seller_remaining[seller.house_id] <= 0:
                    continue
                
                # Skip if seller price exceeds grid price (buyer should import from grid instead)
                if seller.price_lei_kwh >= grid_price:
                    continue
                
                # Skip self-trading
                if seller.house_id == buyer.house_id:
                    continue
                
                # Check line limit
                remaining_capacity = max_trade_kwh - total_traded_kwh
                if remaining_capacity <= 0:
                    break
                
                # Calculate trade amount
                trade_kwh = min(
                    seller_remaining[seller.house_id],
                    buyer_remaining[buyer.house_id],
                    remaining_capacity
                )
                
                if trade_kwh > 0.001:  # Minimum trade threshold
                    trade = TradeMatch(
                        seller_house_id=seller.house_id,
                        buyer_house_id=buyer.house_id,
                        energy_kwh=trade_kwh,
                        price_lei_kwh=seller.price_lei_kwh,
                        total_value_lei=trade_kwh * seller.price_lei_kwh
                    )
                    trades.append(trade)
                    
                    # Update remaining amounts
                    seller_remaining[seller.house_id] -= trade_kwh
                    buyer_remaining[buyer.house_id] -= trade_kwh
                    total_traded_kwh += trade_kwh
                
                # If buyer is satisfied, move to next buyer
                if buyer_remaining[buyer.house_id] <= 0:
                    break
            
            # If line limit reached, stop matching
            if total_traded_kwh >= max_trade_kwh:
                break
        
        return trades
    
    def create_trade_transactions(
        self,
        matches: List[TradeMatch],
        grid_price: float,
        sim_timestamp: datetime
    ) -> List[TradeTransaction]:
        """
        Convert trade matches to trade transactions for database storage.
        
        Args:
            matches: List of trade matches
            grid_price: Grid price at time of trade
            sim_timestamp: Simulation timestamp
        
        Returns:
            List of TradeTransaction objects
        """
        return [
            TradeTransaction(
                seller_house_id=match.seller_house_id,
                buyer_house_id=match.buyer_house_id,
                energy_kwh=match.energy_kwh,
                price_lei_kwh=match.price_lei_kwh,
                total_value_lei=match.total_value_lei,
                grid_price_lei_kwh=grid_price,
                sim_timestamp=sim_timestamp
            )
            for match in matches
        ]
    
    def calculate_savings(
        self,
        matches: List[TradeMatch],
        grid_price: float
    ) -> dict:
        """
        Calculate savings from P2P trading vs grid import.
        
        Args:
            matches: List of trade matches
            grid_price: Grid price
        
        Returns:
            Dictionary with savings statistics
        """
        total_energy = sum(m.energy_kwh for m in matches)
        total_p2p_cost = sum(m.total_value_lei for m in matches)
        total_grid_cost = total_energy * grid_price
        
        buyer_savings = total_grid_cost - total_p2p_cost
        
        return {
            "total_energy_traded_kwh": round(total_energy, 4),
            "total_p2p_cost_lei": round(total_p2p_cost, 2),
            "equivalent_grid_cost_lei": round(total_grid_cost, 2),
            "buyer_savings_lei": round(buyer_savings, 2),
            "avg_discount_percent": round((1 - total_p2p_cost / total_grid_cost) * 100, 1) if total_grid_cost > 0 else 0,
            "trade_count": len(matches)
        }
