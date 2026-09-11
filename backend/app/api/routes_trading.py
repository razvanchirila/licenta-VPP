"""
Trading API routes for P2P energy trading.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.database import get_session_context
from app.services.trading_service import TradingService

router = APIRouter(prefix="/trading", tags=["trading"])


# Request/Response models
class TradingPreferencesUpdate(BaseModel):
    """Request model for updating trading preferences."""
    selling_enabled: Optional[bool] = None
    buying_enabled: Optional[bool] = None
    price_mode: Optional[str] = None  # "fixed" or "discount"
    fixed_price_lei_kwh: Optional[float] = None
    discount_percent: Optional[float] = None
    min_sell_price_lei_kwh: Optional[float] = None


class TradingPreferencesResponse(BaseModel):
    """Response model for trading preferences."""
    house_id: int
    selling_enabled: bool
    buying_enabled: bool
    price_mode: str
    fixed_price_lei_kwh: Optional[float]
    discount_percent: float
    min_sell_price_lei_kwh: float


@router.get("/preferences/{house_id}")
async def get_trading_preferences(house_id: int):
    """Get trading preferences for a house."""
    async with get_session_context() as session:
        service = TradingService(session)
        prefs = await service.get_preferences(house_id)
        
        if not prefs:
            raise HTTPException(status_code=404, detail=f"Trading preferences for house {house_id} not found")
        
        return prefs.to_dict()


@router.put("/preferences/{house_id}")
async def update_trading_preferences(house_id: int, updates: TradingPreferencesUpdate):
    """Update trading preferences for a house."""
    # Validate price_mode
    if updates.price_mode and updates.price_mode not in ["fixed", "discount"]:
        raise HTTPException(status_code=400, detail="price_mode must be 'fixed' or 'discount'")
    
    # Validate discount_percent
    if updates.discount_percent is not None:
        if updates.discount_percent < 0 or updates.discount_percent > 100:
            raise HTTPException(status_code=400, detail="discount_percent must be between 0 and 100")
    
    # Validate fixed_price
    if updates.fixed_price_lei_kwh is not None and updates.fixed_price_lei_kwh < 0:
        raise HTTPException(status_code=400, detail="fixed_price_lei_kwh must be >= 0")
    
    # Validate min_sell_price
    if updates.min_sell_price_lei_kwh is not None and updates.min_sell_price_lei_kwh < 0:
        raise HTTPException(status_code=400, detail="min_sell_price_lei_kwh must be >= 0")
    
    async with get_session_context() as session:
        service = TradingService(session)
        
        # Convert to dict, excluding None values
        updates_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
        
        prefs = await service.update_preferences(house_id, updates_dict)
        
        if not prefs:
            raise HTTPException(status_code=404, detail=f"Trading preferences for house {house_id} not found")
        
        return prefs.to_dict()


@router.get("/history/{house_id}")
async def get_trading_history(
    house_id: int,
    limit: int = Query(default=100, le=500),
    transaction_type: Optional[str] = Query(default=None, description="Filter by 'sell' or 'buy'"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get trading history for a house."""
    if transaction_type and transaction_type not in ["sell", "buy"]:
        raise HTTPException(status_code=400, detail="transaction_type must be 'sell' or 'buy'")
    
    async with get_session_context() as session:
        service = TradingService(session)
        trades = await service.get_trading_history(
            house_id=house_id,
            limit=limit,
            start_date=start_date,
            end_date=end_date,
            transaction_type=transaction_type
        )
        
        return {
            "house_id": house_id,
            "count": len(trades),
            "transactions": [t.to_dict(perspective_house_id=house_id) for t in trades]
        }


@router.get("/stats/{house_id}")
async def get_trading_stats(house_id: int):
    """Get aggregated trading statistics for a house."""
    async with get_session_context() as session:
        service = TradingService(session)
        stats = await service.get_trading_stats(house_id)
        return stats.to_dict()


@router.get("/recent")
async def get_recent_trades(limit: int = Query(default=50, le=200)):
    """Get most recent trades across all houses."""
    async with get_session_context() as session:
        service = TradingService(session)
        trades = await service.get_recent_trades(limit)
        
        return {
            "count": len(trades),
            "transactions": [t.to_dict() for t in trades]
        }


@router.get("/preferences")
async def get_all_trading_preferences():
    """Get trading preferences for all houses."""
    async with get_session_context() as session:
        service = TradingService(session)
        all_prefs = await service.get_all_preferences()
        
        return {
            "count": len(all_prefs),
            "preferences": [p.to_dict() for p in all_prefs]
        }


# ============================================================================
# OPCOM Price Endpoints
# ============================================================================

@router.get("/opcom/prices")
async def get_opcom_prices(
    period: str = Query(default="1Z", description="Period: 1Z (day), 1S (week), 1L (month), 6L, 1A"),
    date: Optional[str] = Query(default=None, description="Date in DD/MM/YYYY format")
):
    """
    Get OPCOM prices for specified period.
    
    Periods:
    - 1Z: 1 day (24 hourly prices)
    - 1S: 1 week (7 daily averages)
    - 1L: 1 month (30 daily averages)
    - 6L: 6 months
    - 1A: 1 year
    """
    from app.services.price_service import PriceService
    
    # Validate period
    valid_periods = ["1Z", "1S", "1L", "6L", "1A"]
    if period not in valid_periods:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
        )
    
    # Parse date if provided
    date_obj = None
    if date:
        try:
            parts = date.split('/')
            if len(parts) == 3:
                day, month, year = map(int, parts)
                date_obj = datetime(year, month, day)
            else:
                raise ValueError("Invalid format")
        except Exception:
            raise HTTPException(status_code=400, detail="Date must be in DD/MM/YYYY format")
    
    async with get_session_context() as session:
        service = PriceService(session)
        price_data = await service.get_prices_for_period(period, date_obj)
        
        return {
            "success": True,
            "data": price_data.to_dict()
        }


@router.get("/opcom/current")
async def get_current_opcom_price():
    """Get current hour's OPCOM price."""
    from app.services.price_service import PriceService
    
    async with get_session_context() as session:
        service = PriceService(session)
        current = await service.get_current_price()
        
        return {
            "success": True,
            "data": current
        }


@router.get("/opcom/history")
async def get_opcom_price_history(
    days: int = Query(default=7, ge=1, le=365, description="Number of days of history")
):
    """Get historical OPCOM prices (daily averages)."""
    from app.services.price_service import PriceService
    
    # Map days to period
    if days <= 1:
        period = "1Z"
    elif days <= 7:
        period = "1S"
    elif days <= 30:
        period = "1L"
    elif days <= 180:
        period = "6L"
    else:
        period = "1A"
    
    async with get_session_context() as session:
        service = PriceService(session)
        price_data = await service.get_prices_for_period(period)
        
        return {
            "success": True,
            "days_requested": days,
            "data": price_data.to_dict()
        }
