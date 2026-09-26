from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import load_house, require_house
from app.api.schemas import DeviceCreate, DeviceUpdate, SettingsUpdate
from app.db.database import get_session
from app.db.repositories import DeviceRepository
from app.services import devices, energy, houses
from app.services.serializers import device_dict
from app.services.simulation_loop import sim

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/house")
async def my_house(house_id: int = Depends(require_house), session: AsyncSession = Depends(get_session)):
    return houses.my_house_dict(await load_house(session, house_id), sim.house_last_step(house_id))


@router.get("/devices")
async def my_devices(house_id: int = Depends(require_house), session: AsyncSession = Depends(get_session)):
    return [device_dict(d) for d in await DeviceRepository(session).get_by_house_id(house_id)]


@router.post("/devices", status_code=201)
async def add_my_device(body: DeviceCreate, house_id: int = Depends(require_house),
                        session: AsyncSession = Depends(get_session)):
    return device_dict(await devices.create_device(session, house_id, body, sim.sim_datetime))


@router.put("/devices/{device_id}")
async def update_my_device(device_id: int, body: DeviceUpdate, house_id: int = Depends(require_house),
                           session: AsyncSession = Depends(get_session)):
    device = await devices.get_device(session, house_id, device_id)
    await devices.update_device(session, device, body, sim.sim_datetime, "user")
    return device_dict(device)


@router.delete("/devices/{device_id}")
async def delete_my_device(device_id: int, house_id: int = Depends(require_house),
                           session: AsyncSession = Depends(get_session)):
    device = await devices.get_device(session, house_id, device_id)
    name = device.name
    await devices.delete_device(session, device)
    return {"device_id": device_id, "name": name, "message": "Dispozitiv sters"}


@router.post("/devices/{device_id}/toggle")
async def toggle_my_device(device_id: int, house_id: int = Depends(require_house),
                           session: AsyncSession = Depends(get_session)):
    device = await devices.get_device(session, house_id, device_id)
    await devices.toggle_device(session, device, sim.sim_datetime, "user")
    return device_dict(device)


@router.get("/settings")
async def my_settings(house_id: int = Depends(require_house), session: AsyncSession = Depends(get_session)):
    return houses.settings_dict(await load_house(session, house_id))


@router.put("/settings")
async def update_my_settings(body: SettingsUpdate, house_id: int = Depends(require_house),
                             session: AsyncSession = Depends(get_session)):
    house = await load_house(session, house_id)
    await houses.update_settings(session, house, body.mode, body.backup_reserve_percent)
    return {**houses.settings_dict(house), "message": "Setari salvate"}


@router.get("/energy/today")
async def energy_today(house_id: int = Depends(require_house), session: AsyncSession = Depends(get_session)):
    start, end = energy.day_bounds(sim.day)
    totals = await energy.period_totals(session, house_id, start, end)
    return {"date": sim.day.isoformat(), "sim_time": sim.sim_datetime.strftime("%H:%M"), **totals}


@router.get("/energy/history")
async def energy_history(days: int = Query(7, ge=1, le=365), house_id: int = Depends(require_house),
                         session: AsyncSession = Depends(get_session)):
    return await energy.daily_totals(session, house_id, sim.day - timedelta(days=days - 1), sim.day)


@router.get("/energy/chart")
async def energy_chart(period: str = Query("day", pattern="^(day|week|month)$"),
                       date_str: str | None = Query(None, alias="date", description="YYYY-MM-DD, implicit azi"),
                       house_id: int = Depends(require_house), session: AsyncSession = Depends(get_session)):
    try:
        ref = date.fromisoformat(date_str) if date_str else sim.day
    except ValueError:
        raise HTTPException(400, "Data trebuie sa fie YYYY-MM-DD") from None
    first, after_last, bucket = energy.chart_range(period, ref, sim.steps_per_day)
    points = await energy.step_points(session, house_id, energy.day_bounds(first)[0], energy.day_bounds(after_last)[0],
                                      bucket)
    return {"period": period, "date": ref.isoformat(), "interval_minutes": int(bucket * sim.dt_h * 60),
            "data_points": points}


@router.get("/energy/impact")
async def energy_impact(house_id: int = Depends(require_house), session: AsyncSession = Depends(get_session)):
    return await energy.impact(session, house_id, sim.day)
