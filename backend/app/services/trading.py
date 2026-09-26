from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TradeTransactionModel as Trade
from app.db.models import TradingPreferencesModel
from app.services.serializers import trade_dict


async def get_preferences(session: AsyncSession, house_id: int) -> TradingPreferencesModel:
    prefs = (await session.execute(
        select(TradingPreferencesModel).where(TradingPreferencesModel.house_id == house_id))).scalar_one_or_none()
    if prefs is None:
        raise HTTPException(404, f"Casa {house_id} nu are preferinte de tranzactionare")
    return prefs


async def list_preferences(session: AsyncSession) -> list[TradingPreferencesModel]:
    rows = await session.execute(select(TradingPreferencesModel).order_by(TradingPreferencesModel.house_id))
    return list(rows.scalars().all())


async def update_preferences(session: AsyncSession, prefs: TradingPreferencesModel, changes: dict) -> None:
    for key, value in changes.items():
        setattr(prefs, key, value)
    await session.flush()


async def history(session: AsyncSession, house_id: int, limit: int, transaction_type: str | None = None,
                  status: str | None = None) -> list[dict]:
    if transaction_type == "sell":
        cond = Trade.seller_house_id == house_id
    elif transaction_type == "buy":
        cond = Trade.buyer_house_id == house_id
    else:
        cond = (Trade.seller_house_id == house_id) | (Trade.buyer_house_id == house_id)
    query = select(Trade).where(cond)
    if status:
        query = query.where(Trade.status == status)
    rows = (await session.execute(query.order_by(Trade.sim_timestamp.desc(), Trade.id.desc()).limit(limit))).scalars()
    return [trade_dict(t, house_id) for t in rows]


async def recent(session: AsyncSession, limit: int) -> list[dict]:
    rows = (await session.execute(select(Trade).order_by(Trade.sim_timestamp.desc(), Trade.id.desc()).limit(limit)))
    return [trade_dict(t) for t in rows.scalars()]


async def _side_totals(session: AsyncSession, cond) -> tuple[int, float, float, float]:
    """(count, kWh, lei, average lei/kWh) over settled trades matching cond."""
    row = (await session.execute(
        select(func.count(Trade.id), func.coalesce(func.sum(Trade.energy_kwh), 0.0),
               func.coalesce(func.sum(Trade.total_value_lei), 0.0)).where(cond, Trade.status == "settled"))).one()
    count, energy, value = int(row[0]), float(row[1]), float(row[2])
    return count, energy, value, (value / energy if energy > 1e-9 else 0.0)


async def stats(session: AsyncSession, house_id: int) -> dict:
    s_count, s_kwh, s_lei, s_avg = await _side_totals(session, Trade.seller_house_id == house_id)
    b_count, b_kwh, b_lei, b_avg = await _side_totals(session, Trade.buyer_house_id == house_id)
    return {
        "house_id": house_id,
        "total_energy_sold_kwh": round(s_kwh, 4), "total_energy_bought_kwh": round(b_kwh, 4),
        "total_earned_lei": round(s_lei, 2), "total_spent_lei": round(b_lei, 2),
        "net_earnings_lei": round(s_lei - b_lei, 2),
        "avg_sell_price_lei_kwh": round(s_avg, 4), "avg_buy_price_lei_kwh": round(b_avg, 4),
        "sell_count": s_count, "buy_count": b_count, "total_trade_count": s_count + b_count,
    }
