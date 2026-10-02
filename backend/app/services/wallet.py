"""Read side only; money movements live in settlement.py."""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import VPPReserveModel, WalletModel, WalletTransactionModel
from app.services.serializers import wallet_tx_dict

TX_TYPES = ("credit", "debit", "vpp_payment", "initial")


async def find_wallet(session: AsyncSession, house_id: int | None) -> WalletModel | None:
    cond = WalletModel.house_id.is_(None) if house_id is None else WalletModel.house_id == house_id
    return (await session.execute(select(WalletModel).where(cond))).scalar_one_or_none()


async def get_wallet(session: AsyncSession, house_id: int | None) -> WalletModel:
    wallet = await find_wallet(session, house_id)
    if wallet is None:
        detail = "Portofelul operatorului nu exista" if house_id is None else f"Casa {house_id} nu are portofel"
        raise HTTPException(404, detail)
    return wallet


async def find_reserve(session: AsyncSession, house_id: int) -> VPPReserveModel | None:
    return (await session.execute(
        select(VPPReserveModel).where(VPPReserveModel.house_id == house_id))).scalar_one_or_none()


async def list_transactions(session: AsyncSession, wallet: WalletModel, limit: int,
                            tx_type: str | None = None) -> list[dict]:
    query = select(WalletTransactionModel).where(WalletTransactionModel.wallet_id == wallet.id)
    if tx_type:
        query = query.where(WalletTransactionModel.transaction_type == tx_type)
    query = query.order_by(WalletTransactionModel.sim_timestamp.desc(), WalletTransactionModel.id.desc()).limit(limit)
    return [wallet_tx_dict(t) for t in (await session.execute(query)).scalars().all()]
