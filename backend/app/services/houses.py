from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HouseModel
from app.services.serializers import battery_dict, house_dict


def my_house_dict(house: HouseModel, last_step: dict | None) -> dict:
    d = house_dict(house, last_step)
    d["house_id"] = house.id
    d["current_consumption_kw"] = round(d["L_crit_kw"] + d["L_noncrit_kw"], 3)
    return d


def settings_dict(house: HouseModel) -> dict:
    battery = house.battery
    reserve = round(100 * battery.soc_min_kwh / battery.capacity_kwh, 1) if battery else None
    return {"mode": house.mode, "backup_reserve_percent": reserve,
            "battery": battery_dict(battery) if battery else None}


async def set_mode(session: AsyncSession, house: HouseModel, mode: str) -> None:
    house.mode = mode
    await session.flush()


async def update_settings(session: AsyncSession, house: HouseModel, mode: str | None,
                          backup_reserve_percent: float | None) -> None:
    if mode is not None:
        house.mode = mode
    if backup_reserve_percent is not None and house.battery is not None:
        house.battery.soc_min_kwh = round(house.battery.capacity_kwh * backup_reserve_percent / 100, 3)
    await session.flush()
