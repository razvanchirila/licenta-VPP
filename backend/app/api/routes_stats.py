from dataclasses import asdict
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import check_house_access, get_current_user
from app.db.database import get_session
from app.db.models import UserModel
from app.services.analytics_service import AnalyticsService, TimePeriod
from app.services.simulation_loop import sim

router = APIRouter(prefix="/stats", tags=["stats"])

# the longest view of the app, "An", starts on the 1st of the same month one year back: at most 366 + 30 days
MAX_CHART_DAYS = 400


def stats_house_id(house_id: int | None = Query(None, ge=1), user: UserModel = Depends(get_current_user)) -> int:
    """Own house by default; admins may ask for any house with ?house_id=."""
    target = house_id if house_id is not None else user.house_id
    if target is None:
        raise HTTPException(403, "Utilizatorul nu are o casa asignata")
    check_house_access(user, target)
    return target


def _period(period: str) -> TimePeriod:
    try:
        return TimePeriod(period.lower())
    except ValueError:
        raise HTTPException(400, "Perioada trebuie sa fie day, week, month sau year") from None


def _analytics(session: AsyncSession) -> AnalyticsService:
    return AnalyticsService(session, now=sim.sim_datetime)


@router.get("/summary")
async def summary(period: str = Query("month"), house_id: int = Depends(stats_house_id),
                  session: AsyncSession = Depends(get_session)):
    return asdict(await _analytics(session).consumption_summary(house_id, _period(period)))


@router.get("/top-consumers")
async def top_consumers(period: str = Query("month"), limit: int = Query(10, ge=1, le=50),
                        house_id: int = Depends(stats_house_id), session: AsyncSession = Depends(get_session)):
    total_kwh, rows = await _analytics(session).top_consumers(house_id, _period(period), limit)
    return {"period": period, "total_house_kwh": total_kwh, "devices": [asdict(d) for d in rows]}


@router.get("/chart")
async def chart(start_date: str = Query(..., description="YYYY-MM-DD"),
                end_date: str = Query(..., description="YYYY-MM-DD"),
                house_id: int = Depends(stats_house_id), session: AsyncSession = Depends(get_session)):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(400, "Datele trebuie sa fie YYYY-MM-DD") from None
    if end < start:
        raise HTTPException(400, "end_date trebuie sa fie dupa start_date")
    if (end - start).days > MAX_CHART_DAYS:
        raise HTTPException(400, f"Intervalul poate avea cel mult {MAX_CHART_DAYS} de zile")
    granularity, points = await _analytics(session).chart_data(house_id, start, end)
    return {"granularity": granularity, "start_date": start_date, "end_date": end_date,
            "data_points": [{"timestamp": p.timestamp.isoformat(), "value_kwh": p.value_kwh} for p in points]}


@router.get("/comparison")
async def comparison(house_id: int = Depends(stats_house_id), session: AsyncSession = Depends(get_session)):
    return asdict(await _analytics(session).monthly_comparison(house_id))
