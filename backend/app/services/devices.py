"""Every toggle is written to energy_logs; the per-step energy is added by the simulation loop."""
from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import DeviceCreate, DeviceUpdate
from app.db.models import DeviceModel
from app.db.repositories import DeviceRepository, EnergyLogRepository


async def get_device(session: AsyncSession, house_id: int, device_id: int) -> DeviceModel:
    device = await DeviceRepository(session).get_by_id(device_id)
    if device is None or device.house_id != house_id:
        raise HTTPException(404, "Dispozitivul nu exista in aceasta casa")
    return device


async def create_device(session: AsyncSession, house_id: int, body: DeviceCreate, sim_ts: datetime) -> DeviceModel:
    device = DeviceModel(house_id=house_id, name=body.name, power_w=body.power_w, critical=body.critical,
                         status_on=body.status_on, last_state_change_ts=sim_ts if body.status_on else None)
    session.add(device)
    await session.flush()
    if body.status_on:
        _log_toggle(session, device, sim_ts, by="create")
    return device


async def update_device(session: AsyncSession, device: DeviceModel, body: DeviceUpdate, sim_ts: datetime,
                        by: str) -> DeviceModel:
    if body.name is not None:
        device.name = body.name
    if body.power_w is not None:
        device.power_w = body.power_w
    if body.critical is not None:
        device.critical = body.critical
    if body.status_on is not None and body.status_on != device.status_on:
        await set_status(session, device, body.status_on, sim_ts, by)
    await session.flush()
    return device


async def set_status(session: AsyncSession, device: DeviceModel, on: bool, sim_ts: datetime, by: str) -> None:
    if not on and device.critical:
        raise HTTPException(400, "Un dispozitiv critic nu poate fi oprit")
    device.status_on = on
    device.last_state_change_ts = sim_ts
    if not on:
        device.current_power_kw = 0.0
    _log_toggle(session, device, sim_ts, by)
    await session.flush()


async def toggle_device(session: AsyncSession, device: DeviceModel, sim_ts: datetime, by: str) -> DeviceModel:
    await set_status(session, device, not device.status_on, sim_ts, by)
    return device


async def delete_device(session: AsyncSession, device: DeviceModel) -> None:
    if device.critical:
        raise HTTPException(400, "Un dispozitiv critic nu poate fi sters")
    await session.delete(device)
    await session.flush()


def _log_toggle(session: AsyncSession, device: DeviceModel, sim_ts: datetime, by: str) -> None:
    details = json.dumps({"power_w": device.power_w, "triggered_by": by})
    EnergyLogRepository(session).log_event(device.id, "toggle_on" if device.status_on else "toggle_off", sim_ts,
                                           details=details)
