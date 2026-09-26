from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin, require_house_access
from app.api.schemas import TradingPreferencesUpdate
from app.db.database import get_session
from app.db.models import UserModel
from app.services import trading
from app.services.serializers import prefs_dict

router = APIRouter(prefix="/trading", tags=["trading"])


@router.get("/preferences")
async def all_preferences(_: UserModel = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    prefs = [prefs_dict(p) for p in await trading.list_preferences(session)]
    return {"count": len(prefs), "preferences": prefs}


@router.get("/preferences/{house_id}")
async def get_preferences(house_id: int, _: UserModel = Depends(require_house_access),
                          session: AsyncSession = Depends(get_session)):
    return prefs_dict(await trading.get_preferences(session, house_id))


@router.put("/preferences/{house_id}")
async def update_preferences(house_id: int, body: TradingPreferencesUpdate,
                             _: UserModel = Depends(require_house_access),
                             session: AsyncSession = Depends(get_session)):
    """Only selling_enabled / buying_enabled influence the simulation (see api.md)."""
    prefs = await trading.get_preferences(session, house_id)
    await trading.update_preferences(session, prefs, body.model_dump(exclude_none=True))
    return prefs_dict(prefs)


@router.get("/history/{house_id}")
async def history(house_id: int, limit: int = Query(100, ge=1, le=500),
                  transaction_type: str | None = Query(None, pattern="^(sell|buy)$"),
                  status: str | None = Query(None, pattern="^(settled|rejected)$"),
                  _: UserModel = Depends(require_house_access), session: AsyncSession = Depends(get_session)):
    rows = await trading.history(session, house_id, limit, transaction_type, status)
    return {"house_id": house_id, "count": len(rows), "transactions": rows}


@router.get("/stats/{house_id}")
async def stats(house_id: int, _: UserModel = Depends(require_house_access),
                session: AsyncSession = Depends(get_session)):
    return await trading.stats(session, house_id)


@router.get("/recent")
async def recent(limit: int = Query(50, ge=1, le=500), _: UserModel = Depends(require_admin),
                 session: AsyncSession = Depends(get_session)):
    rows = await trading.recent(session, limit)
    return {"count": len(rows), "transactions": rows}
