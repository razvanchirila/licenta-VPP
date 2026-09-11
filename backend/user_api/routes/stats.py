"""Statistics routes - /me/stats/* endpoints for energy analytics."""
from dataclasses import asdict
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.models.analytics import TimePeriod
from app.services.analytics_service import AnalyticsService
from user_api.middleware import get_current_user


router = APIRouter(prefix="/me/stats", tags=["statistics"])


def parse_period(period: str) -> TimePeriod:
    """Parse period string to TimePeriod enum."""
    try:
        return TimePeriod(period.lower())
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid period. Must be one of: day, week, month, year"
        )


@router.get("/summary")
async def get_consumption_summary(
    period: str = Query("month", description="Time period: day, week, month, year"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get consumption summary for user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    time_period = parse_period(period)
    service = AnalyticsService(session)
    
    summary = await service.get_consumption_summary(
        house_id=house_id,
        period=time_period
    )
    
    return asdict(summary)


@router.get("/top-consumers")
async def get_top_consumers(
    period: str = Query("month", description="Time period: day, week, month, year"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of devices to return"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get top energy consuming devices for user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    time_period = parse_period(period)
    service = AnalyticsService(session)
    
    # Get total for house to include in response
    summary = await service.get_consumption_summary(
        house_id=house_id,
        period=time_period
    )
    
    devices = await service.get_top_consumers(
        house_id=house_id,
        period=time_period,
        limit=limit
    )
    
    return {
        "period": period,
        "total_house_kwh": summary.total_kwh,
        "devices": [asdict(d) for d in devices]
    }


@router.get("/chart")
async def get_chart_data(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get chart data for consumption visualization."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59
        )
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    if end < start:
        raise HTTPException(
            status_code=400, 
            detail="End date must be after start date"
        )
    
    if start > datetime.now():
        raise HTTPException(
            status_code=400, 
            detail="Cannot query future dates"
        )
    
    service = AnalyticsService(session)
    granularity, data_points = await service.get_chart_data(
        house_id=house_id,
        start_date=start,
        end_date=end
    )
    
    return {
        "granularity": granularity,
        "start_date": start_date,
        "end_date": end_date,
        "data_points": [
            {
                "timestamp": dp.timestamp.isoformat(),
                "value_kwh": dp.value_kwh
            }
            for dp in data_points
        ]
    }


@router.get("/comparison")
async def get_monthly_comparison(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get comparison between current and previous month."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    service = AnalyticsService(session)
    comparison = await service.get_monthly_comparison(house_id=house_id)
    
    return asdict(comparison)
