"""
Trading routes for User API - P2P energy trading endpoints.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from app.db.database import get_session_context
from app.services.trading_service import TradingService
from app.services.wallet_service import WalletService
from ..middleware.jwt_middleware import get_current_user

router = APIRouter(tags=["trading"])


class TradingPreferencesUpdate(BaseModel):
    """Request model for updating trading preferences."""
    selling_enabled: Optional[bool] = None
    buying_enabled: Optional[bool] = None
    price_mode: Optional[str] = None
    fixed_price_lei_kwh: Optional[float] = None
    discount_percent: Optional[float] = None
    min_sell_price_lei_kwh: Optional[float] = None


# ============================================================
# TRADING PREFERENCES
# ============================================================

@router.get("/trading/preferences/{house_id}")
async def get_trading_preferences(house_id: int, user: dict = Depends(get_current_user)):
    """Get trading preferences for a house."""
    # Users can only access their own house (unless admin)
    if user.get("house_id") != house_id and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    async with get_session_context() as session:
        service = TradingService(session)
        prefs = await service.get_preferences(house_id)
        
        if not prefs:
            raise HTTPException(status_code=404, detail=f"Trading preferences for house {house_id} not found")
        
        return prefs.to_dict()


@router.put("/trading/preferences/{house_id}")
async def update_trading_preferences(
    house_id: int,
    updates: TradingPreferencesUpdate,
    user: dict = Depends(get_current_user)
):
    """Update trading preferences for a house."""
    if user.get("house_id") != house_id and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if updates.price_mode and updates.price_mode not in ["fixed", "discount"]:
        raise HTTPException(status_code=400, detail="price_mode must be 'fixed' or 'discount'")
    
    if updates.discount_percent is not None:
        if updates.discount_percent < 0 or updates.discount_percent > 100:
            raise HTTPException(status_code=400, detail="discount_percent must be between 0 and 100")
    
    async with get_session_context() as session:
        service = TradingService(session)
        updates_dict = {k: v for k, v in updates.model_dump().items() if v is not None}
        prefs = await service.update_preferences(house_id, updates_dict)
        
        if not prefs:
            raise HTTPException(status_code=404, detail=f"Trading preferences for house {house_id} not found")
        
        return prefs.to_dict()


# ============================================================
# TRADING HISTORY
# ============================================================

@router.get("/trading/history/{house_id}")
async def get_trading_history(
    house_id: int,
    limit: int = Query(default=100, le=500),
    transaction_type: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user)
):
    """Get trading history for a house."""
    if user.get("house_id") != house_id and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    async with get_session_context() as session:
        service = TradingService(session)
        trades = await service.get_trading_history(
            house_id=house_id,
            limit=limit,
            transaction_type=transaction_type
        )
        
        return {
            "house_id": house_id,
            "count": len(trades),
            "transactions": [t.to_dict(perspective_house_id=house_id) for t in trades]
        }


@router.get("/trading/stats/{house_id}")
async def get_trading_stats(house_id: int, user: dict = Depends(get_current_user)):
    """Get trading statistics for a house."""
    if user.get("house_id") != house_id and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    async with get_session_context() as session:
        service = TradingService(session)
        stats = await service.get_trading_stats(house_id)
        return stats.to_dict()


# ============================================================
# WALLET
# ============================================================

@router.get("/wallet/{house_id}")
async def get_wallet(house_id: int, user: dict = Depends(get_current_user)):
    """Get wallet for a house."""
    if user.get("house_id") != house_id and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    async with get_session_context() as session:
        service = WalletService(session)
        wallet = await service.get_wallet(house_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail=f"Wallet for house {house_id} not found")
        
        return wallet.to_dict()


@router.get("/wallet/{house_id}/transactions")
async def get_wallet_transactions(
    house_id: int,
    limit: int = Query(default=50, le=200),
    transaction_type: Optional[str] = Query(default=None),
    user: dict = Depends(get_current_user)
):
    """Get wallet transactions for a house."""
    if user.get("house_id") != house_id and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    async with get_session_context() as session:
        wallet_service = WalletService(session)
        wallet = await wallet_service.get_wallet(house_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail=f"Wallet for house {house_id} not found")
        
        transactions = await wallet_service.get_transactions(
            house_id=house_id,
            limit=limit,
            transaction_type=transaction_type
        )
        
        return {
            "house_id": house_id,
            "current_balance_lei": wallet.balance_lei,
            "count": len(transactions),
            "transactions": [t.to_dict() for t in transactions]
        }


# ============================================================
# OPCOM PRICE ENDPOINTS
# ============================================================

@router.get("/trading/opcom/prices")
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


@router.get("/trading/opcom/current")
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


@router.get("/trading/opcom/history")
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


class TransferToVPPRequest(BaseModel):
    energy_kwh: float


@router.post("/wallet/{house_id}/transfer-to-vpp")
async def transfer_to_vpp(
    house_id: int,
    request: TransferToVPPRequest,
    user: dict = Depends(get_current_user)
):
    """Transfer energy to VPP reserve."""
    if user.get("house_id") != house_id and not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if request.energy_kwh <= 0:
        raise HTTPException(status_code=400, detail="energy_kwh must be > 0")
    
    # Import here to avoid circular imports
    from app.api.state import vpp_state
    from app.db.repositories.vpp_reserve_repository import VPPReserveRepository
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    house = vpp_state.vpp.get_house(house_id)
    if not house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    if not house.battery:
        raise HTTPException(status_code=400, detail=f"House {house_id} does not have a battery")
    
    available_kwh = house.battery.soc_kwh - house.battery.soc_min_kwh
    if request.energy_kwh > available_kwh:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient available SOC. Available: {available_kwh:.2f} kWh"
        )
    
    async with get_session_context() as session:
        reserve_repo = VPPReserveRepository(session)
        reserve = await reserve_repo.get_by_house_id(house_id)
        
        if not reserve:
            raise HTTPException(status_code=404, detail=f"VPP reserve for house {house_id} not found")
        
        payment_lei = request.energy_kwh * reserve.base_rate_lei_kwh
        await reserve_repo.add_reserve(house_id, request.energy_kwh)
        
        wallet_service = WalletService(session)
        wallet = await wallet_service.credit_wallet(
            house_id=house_id,
            amount=payment_lei,
            description=f"VPP reserve contribution: {request.energy_kwh:.2f} kWh"
        )
        
        house.battery.soc_kwh -= request.energy_kwh
        updated_reserve = await reserve_repo.get_by_house_id(house_id)
        
        return {
            "success": True,
            "house_id": house_id,
            "energy_transferred_kwh": request.energy_kwh,
            "payment_lei": round(payment_lei, 2),
            "new_battery_soc_kwh": round(house.battery.soc_kwh, 2),
            "wallet_balance_lei": round(wallet.balance_lei, 2) if wallet else None
        }
