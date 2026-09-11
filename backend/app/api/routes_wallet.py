"""
Wallet API routes for P2P energy trading.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db.database import get_session_context
from app.services.wallet_service import WalletService

router = APIRouter(prefix="/wallet", tags=["wallet"])


class WalletResponse(BaseModel):
    """Response model for wallet."""
    house_id: int
    balance_lei: float
    total_earned_lei: float
    total_spent_lei: float
    net_balance_lei: float
    transaction_count: int
    is_flagged: bool
    is_consistent: bool


class TransferToVPPRequest(BaseModel):
    """Request model for transferring energy to VPP reserve."""
    energy_kwh: float


@router.get("/{house_id}")
async def get_wallet(house_id: int):
    """Get wallet for a house."""
    async with get_session_context() as session:
        service = WalletService(session)
        wallet = await service.get_wallet(house_id)
        
        if not wallet:
            raise HTTPException(status_code=404, detail=f"Wallet for house {house_id} not found")
        
        return wallet.to_dict()


@router.get("/{house_id}/transactions")
async def get_wallet_transactions(
    house_id: int,
    limit: int = Query(default=50, le=200),
    transaction_type: Optional[str] = Query(default=None, description="Filter by 'credit', 'debit', or 'vpp_bonus'")
):
    """Get wallet transactions for a house."""
    if transaction_type and transaction_type not in ["credit", "debit", "vpp_bonus"]:
        raise HTTPException(status_code=400, detail="transaction_type must be 'credit', 'debit', or 'vpp_bonus'")
    
    async with get_session_context() as session:
        service = WalletService(session)
        
        # First check if wallet exists
        wallet = await service.get_wallet(house_id)
        if not wallet:
            raise HTTPException(status_code=404, detail=f"Wallet for house {house_id} not found")
        
        transactions = await service.get_transactions(
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


@router.post("/{house_id}/transfer-to-vpp")
async def transfer_to_vpp(house_id: int, request: TransferToVPPRequest):
    """
    Transfer energy from battery to VPP reserve.
    
    This deducts energy from the house's battery SOC and adds it to the VPP reserve.
    The user receives immediate payment at the base rate.
    """
    from app.api.state import vpp_state
    from app.db.repositories.vpp_reserve_repository import VPPReserveRepository
    
    if request.energy_kwh <= 0:
        raise HTTPException(status_code=400, detail="energy_kwh must be > 0")
    
    # Check if house exists and has battery
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    house = vpp_state.vpp.get_house(house_id)
    if not house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    if not house.battery:
        raise HTTPException(status_code=400, detail=f"House {house_id} does not have a battery")
    
    # Check if enough SOC available (above minimum)
    available_kwh = house.battery.soc_kwh - house.battery.soc_min_kwh
    if request.energy_kwh > available_kwh:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient available SOC. Available: {available_kwh:.2f} kWh, Requested: {request.energy_kwh:.2f} kWh"
        )
    
    async with get_session_context() as session:
        # Get VPP reserve
        reserve_repo = VPPReserveRepository(session)
        reserve = await reserve_repo.get_by_house_id(house_id)
        
        if not reserve:
            raise HTTPException(status_code=404, detail=f"VPP reserve for house {house_id} not found")
        
        # Calculate payment
        payment_lei = request.energy_kwh * reserve.base_rate_lei_kwh
        
        # Update VPP reserve
        await reserve_repo.add_reserve(house_id, request.energy_kwh)
        
        # Credit wallet
        wallet_service = WalletService(session)
        wallet = await wallet_service.credit_wallet(
            house_id=house_id,
            amount=payment_lei,
            description=f"VPP reserve contribution: {request.energy_kwh:.2f} kWh"
        )
        
        # Deduct from battery SOC (in memory model)
        house.battery.soc_kwh -= request.energy_kwh
        
        # Get updated reserve
        updated_reserve = await reserve_repo.get_by_house_id(house_id)
        
        return {
            "success": True,
            "house_id": house_id,
            "energy_transferred_kwh": request.energy_kwh,
            "payment_lei": round(payment_lei, 2),
            "new_battery_soc_kwh": round(house.battery.soc_kwh, 2),
            "new_battery_soc_percent": round(house.battery.get_soc_percent(), 1),
            "vpp_reserve": updated_reserve.to_dict() if updated_reserve else None,
            "wallet_balance_lei": round(wallet.balance_lei, 2) if wallet else None
        }
