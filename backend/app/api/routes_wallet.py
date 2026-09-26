from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_house_access
from app.api.schemas import TransferToVPPRequest
from app.db.database import get_session
from app.db.models import UserModel
from app.services import wallet as wallets
from app.services.serializers import reserve_dict, wallet_dict
from app.services.settlement import SettlementError
from app.services.simulation_loop import sim

router = APIRouter(prefix="/wallet", tags=["wallet"])

TX_TYPE_PATTERN = "^(" + "|".join(wallets.TX_TYPES) + ")$"


@router.get("/operator")
async def operator_wallet(limit: int = Query(50, ge=1, le=500), _: UserModel = Depends(require_admin),
                          session: AsyncSession = Depends(get_session)):
    wallet = await wallets.get_wallet(session, None)
    return {**wallet_dict(wallet), "transactions": await wallets.list_transactions(session, wallet, limit)}


@router.get("/{house_id}")
async def get_wallet(house_id: int, _: UserModel = Depends(require_house_access),
                     session: AsyncSession = Depends(get_session)):
    wallet = await wallets.get_wallet(session, house_id)
    reserve = await wallets.find_reserve(session, house_id)
    return {**wallet_dict(wallet), "vpp_reserve": reserve_dict(reserve) if reserve else None}


@router.get("/{house_id}/transactions")
async def transactions(house_id: int, limit: int = Query(50, ge=1, le=500),
                       transaction_type: str | None = Query(None, pattern=TX_TYPE_PATTERN),
                       _: UserModel = Depends(require_house_access), session: AsyncSession = Depends(get_session)):
    wallet = await wallets.get_wallet(session, house_id)
    items = await wallets.list_transactions(session, wallet, limit, transaction_type)
    return {"house_id": house_id, "current_balance_lei": round(wallet.balance_lei, 2), "count": len(items),
            "transactions": items}


@router.post("/{house_id}/transfer-to-vpp")
async def transfer_to_vpp(house_id: int, body: TransferToVPPRequest, _: UserModel = Depends(require_house_access),
                          session: AsyncSession = Depends(get_session)):
    await wallets.get_wallet(session, house_id)
    try:
        payment, new_soc, wallet = await sim.withdraw_from_battery(house_id, body.energy_kwh)
    except (ValueError, SettlementError) as e:
        raise HTTPException(400, str(e)) from None
    reserve = await wallets.find_reserve(session, house_id)
    return {
        "success": True,
        "house_id": house_id,
        "energy_transferred_kwh": body.energy_kwh,
        "payment_lei": round(payment, 2),
        "new_battery_soc_kwh": round(new_soc, 3),
        "wallet_balance_lei": round(wallet.balance_lei, 2),
        "vpp_reserve": reserve_dict(reserve),
    }
