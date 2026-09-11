"""User's house and device routes - /me/* endpoints."""
import logging
import math as _math
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.db.database import get_session
from app.db.models import HouseModel, DeviceModel, EnergyLogModel
from app.db.repositories import HouseRepository, DeviceRepository
from app.db.repositories.energy_log_repository import EnergyLogRepository
from user_api.middleware import get_current_user


def get_sim_datetime():
    """Get current simulation datetime."""
    try:
        from app.services.simulation_loop import simulation_loop
        return simulation_loop.clock.sim_datetime
    except Exception:
        from datetime import datetime
        return datetime.now()

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/me", tags=["my-house"])


# Pydantic models for requests
class DeviceCreate(BaseModel):
    name: str
    power_w: float
    critical: bool = False
    status_on: bool = False


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    power_w: Optional[float] = None
    critical: Optional[bool] = None


class SettingsUpdate(BaseModel):
    mode: Optional[str] = None              # "Eco" or "Profit"
    backup_reserve_percent: Optional[float] = None  # 0-60


@router.get("/house")
async def get_my_house(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current user's house with battery and consumption info."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    house_repo = HouseRepository(session)
    house = await house_repo.get_by_id_with_relations(house_id)
    
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    
    # Get live data from VPP state (simulation memory) if available
    live_battery_soc = None
    live_consumption_kw = None
    try:
        from app.api.state import vpp_state
        if vpp_state.vpp:
            mem_house = vpp_state.vpp.get_house(house_id)
            if mem_house:
                # Get live consumption from in-memory devices
                live_consumption_kw = sum(
                    d.get_power_kw() for d in mem_house.devices if d.status_on
                )
                # Get live battery SOC from simulation
                if mem_house.battery:
                    live_battery_soc = mem_house.battery.soc_kwh
    except Exception:
        pass
    
    # Calculate current consumption from DB (fallback)
    db_consumption_kw = sum(
        d.power_w / 1000 for d in house.devices if d.status_on
    )
    
    # Use live data if available, otherwise DB data
    current_consumption_kw = live_consumption_kw if live_consumption_kw is not None else db_consumption_kw
    
    # Battery info - prefer live SOC from simulation
    battery_info = None
    if house.battery:
        soc_kwh = live_battery_soc if live_battery_soc is not None else house.battery.soc_kwh
        battery_info = {
            "capacity_kwh": house.battery.capacity_kwh,
            "soc_kwh": round(soc_kwh, 2),
            "soc_percent": round((soc_kwh / house.battery.capacity_kwh) * 100, 1),
            "p_ch_max_kw": house.battery.p_ch_max_kw,
            "p_dis_max_kw": house.battery.p_dis_max_kw
        }
    
    return {
        "house_id": house.id,
        "name": house.name,
        "mode": house.mode,
        "has_pv": house.has_pv,
        "pv_capacity_kw": house.pv_capacity_kw,
        "battery": battery_info,
        "current_consumption_kw": round(current_consumption_kw, 3),
        "device_count": len(house.devices)
    }


@router.get("/devices")
async def get_my_devices(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get all devices in user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    device_repo = DeviceRepository(session)
    devices = await device_repo.get_by_house_id(house_id)
    
    # Get live device states from VPP memory if available
    live_devices = {}
    try:
        from app.api.state import vpp_state
        if vpp_state.vpp:
            mem_house = vpp_state.vpp.get_house(house_id)
            if mem_house:
                for d in mem_house.devices:
                    live_devices[d.id] = d
    except Exception:
        pass
    
    result = []
    sim_time = get_sim_datetime()
    
    for d in devices:
        # Prefer live data from simulation memory
        live_d = live_devices.get(d.id)
        if live_d:
            pending = live_d.calculate_pending_energy(sim_time)
            accumulated = live_d.accumulated_energy_kwh
            result.append({
                "id": d.id,
                "name": d.name,
                "power_w": d.power_w,
                "status_on": live_d.status_on,
                "critical": d.critical,
                "current_power_kw": live_d.get_power_kw(),
                "accumulated_energy_kwh": round(accumulated, 4),
                "pending_energy_kwh": round(pending, 4),
                "total_energy_kwh": round(accumulated + pending, 4)
            })
        else:
            # Calculate pending from DB data
            pending = 0.0
            if d.status_on and d.last_state_change_ts:
                duration = sim_time - d.last_state_change_ts
                duration_hours = duration.total_seconds() / 3600
                pending = (d.power_w / 1000) * duration_hours
            
            result.append({
                "id": d.id,
                "name": d.name,
                "power_w": d.power_w,
                "status_on": d.status_on,
                "critical": d.critical,
                "current_power_kw": d.power_w / 1000 if d.status_on else 0,
                "accumulated_energy_kwh": round(d.accumulated_energy_kwh, 4),
                "pending_energy_kwh": round(pending, 4),
                "total_energy_kwh": round(d.accumulated_energy_kwh + pending, 4)
            })
    
    return result



@router.post("/devices")
async def create_my_device(
    device_data: DeviceCreate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Add a new device to user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    # Validate power
    if device_data.power_w <= 0:
        raise HTTPException(status_code=400, detail="Power must be positive")
    if device_data.power_w > 50000:  # 50kW max
        raise HTTPException(status_code=400, detail="Power exceeds maximum (50kW)")
    
    # Create device in DB - use simulation time
    current_time = get_sim_datetime()
    new_device = DeviceModel(
        house_id=house_id,
        name=device_data.name,
        power_w=device_data.power_w,
        critical=device_data.critical,
        status_on=device_data.status_on,
        accumulated_energy_kwh=0.0,
        last_state_change_ts=current_time if device_data.status_on else None
    )
    session.add(new_device)
    await session.flush()
    await session.refresh(new_device)
    
    # Sync with in-memory VPP state
    try:
        from app.api.state import vpp_state
        from app.models.device import Device as MemDevice
        if vpp_state.vpp:
            mem_house = vpp_state.vpp.get_house(house_id)
            if mem_house:
                mem_device = MemDevice(
                    id=new_device.id,
                    name=new_device.name,
                    power_w=new_device.power_w,
                    critical=new_device.critical,
                    status_on=new_device.status_on,
                    last_state_change_ts=new_device.last_state_change_ts,
                    accumulated_energy_kwh=0.0
                )
                mem_house.add_device(mem_device)
                logger.info(f"Added device {new_device.id} to VPP memory for house {house_id}")
    except Exception as e:
        logger.warning(f"Failed to sync new device to VPP state: {e}")
    
    return {
        "id": new_device.id,
        "name": new_device.name,
        "power_w": new_device.power_w,
        "critical": new_device.critical,
        "status_on": new_device.status_on,
        "message": "Device created successfully"
    }


@router.put("/devices/{device_id}")
async def update_my_device(
    device_id: int,
    device_data: DeviceUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update a device in user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    device_repo = DeviceRepository(session)
    device = await device_repo.get_by_id(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.house_id != house_id:
        raise HTTPException(status_code=403, detail="Device does not belong to your house")
    
    # Track changes for logging
    old_power = device.power_w
    old_critical = device.critical
    import json
    
    # Update fields if provided
    if device_data.name is not None:
        device.name = device_data.name
    if device_data.power_w is not None:
        if device_data.power_w <= 0:
            raise HTTPException(status_code=400, detail="Power must be positive")
        device.power_w = device_data.power_w
    if device_data.critical is not None:
        device.critical = device_data.critical
    
    await session.flush()
    await session.refresh(device)
    
    # Log changes to energy_logs
    energy_log_repo = EnergyLogRepository(session)
    
    # Log power change
    if device_data.power_w is not None and old_power != device.power_w:
        details = json.dumps({
            "old_power_w": old_power,
            "new_power_w": device.power_w,
            "change_type": "power_change"
        })
        await energy_log_repo.create(EnergyLogModel(
            device_id=device_id,
            energy_kwh=0.0,
            event_type="power_change",
            details=details
        ))
        logger.info(f"Logged power_change for device {device_id}: {old_power}W -> {device.power_w}W")
    
    # Log critical status change
    if device_data.critical is not None and old_critical != device.critical:
        details = json.dumps({
            "old_critical": old_critical,
            "new_critical": device.critical,
            "change_type": "critical_change"
        })
        await energy_log_repo.create(EnergyLogModel(
            device_id=device_id,
            energy_kwh=0.0,
            event_type="critical_change",
            details=details
        ))
        logger.info(f"Logged critical_change for device {device_id}: {old_critical} -> {device.critical}")
    
    # Sync with in-memory VPP state
    try:
        from app.api.state import vpp_state
        if vpp_state.vpp:
            mem_house = vpp_state.vpp.get_house(house_id)
            if mem_house:
                mem_device = mem_house.get_device(device_id)
                if mem_device:
                    mem_device.name = device.name
                    mem_device.power_w = device.power_w
                    mem_device.critical = device.critical
    except Exception as e:
        logger.warning(f"Failed to sync device update to VPP state: {e}")
    
    return {
        "id": device.id,
        "name": device.name,
        "power_w": device.power_w,
        "critical": device.critical,
        "status_on": device.status_on,
        "message": "Device updated successfully"
    }


@router.delete("/devices/{device_id}")
async def delete_my_device(
    device_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Delete a device from user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    device_repo = DeviceRepository(session)
    device = await device_repo.get_by_id(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.house_id != house_id:
        raise HTTPException(status_code=403, detail="Device does not belong to your house")
    
    if device.critical:
        raise HTTPException(status_code=400, detail="Cannot delete critical device")
    
    device_name = device.name
    await session.delete(device)
    await session.flush()
    
    # Sync with in-memory VPP state
    try:
        from app.api.state import vpp_state
        if vpp_state.vpp:
            mem_house = vpp_state.vpp.get_house(house_id)
            if mem_house:
                mem_house.remove_device(device_id)
                logger.info(f"Removed device {device_id} from VPP memory for house {house_id}")
    except Exception as e:
        logger.warning(f"Failed to sync device deletion to VPP state: {e}")
    
    return {
        "device_id": device_id,
        "name": device_name,
        "message": "Device deleted successfully"
    }


@router.post("/devices/{device_id}/toggle")
async def toggle_my_device(
    device_id: int,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Toggle a device on/off in user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    device_repo = DeviceRepository(session)
    
    # Get device and verify it belongs to user's house
    device = await device_repo.get_by_id(device_id)
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    if device.house_id != house_id:
        raise HTTPException(status_code=403, detail="Device does not belong to your house")
    
    if device.critical and device.status_on:
        raise HTTPException(status_code=400, detail="Cannot turn off critical device")
    
    # Calculate energy if turning OFF - use simulation time
    energy_calculated = 0.0
    current_time = get_sim_datetime()
    was_on = device.status_on
    
    if device.status_on and device.last_state_change_ts:
        # Device was ON, calculate energy consumed
        duration = current_time - device.last_state_change_ts
        duration_hours = duration.total_seconds() / 3600
        power_kw = device.power_w / 1000
        energy_calculated = power_kw * duration_hours
        device.accumulated_energy_kwh += energy_calculated
    
    # Toggle status in DB
    device.status_on = not device.status_on
    device.last_state_change_ts = current_time
    
    await session.flush()
    await session.refresh(device)
    
    # Log to energy_logs table for analytics
    energy_log_repo = EnergyLogRepository(session)
    import json
    
    if was_on:
        # Device turned OFF - log energy consumed
        details = json.dumps({
            "duration_hours": round(duration_hours, 4) if 'duration_hours' in dir() else 0,
            "power_w": device.power_w,
            "triggered_by": "user"
        })
        await energy_log_repo.log_toggle_off(
            device_id=device_id,
            energy_kwh=energy_calculated,
            details=details
        )
        logger.info(f"Logged toggle_off for device {device_id}: {energy_calculated:.4f} kWh")
    else:
        # Device turned ON - log start time
        details = json.dumps({
            "power_w": device.power_w,
            "triggered_by": "user"
        })
        await energy_log_repo.log_toggle_on(
            device_id=device_id,
            details=details
        )
        logger.info(f"Logged toggle_on for device {device_id}")
    
    # IMPORTANT: Sync with in-memory VPP state for simulation
    try:
        from app.api.state import vpp_state
        if vpp_state.vpp:
            mem_house = vpp_state.vpp.get_house(house_id)
            if mem_house:
                mem_device = mem_house.get_device(device_id)
                if mem_device:
                    mem_device.status_on = device.status_on
                    mem_device.last_state_change_ts = device.last_state_change_ts
                    mem_device.accumulated_energy_kwh = device.accumulated_energy_kwh
    except Exception as e:
        # Log but don't fail the request
        logger.warning(f"Failed to sync device to VPP state: {e}")
    
    return {
        "device_id": device.id,
        "name": device.name,
        "status_on": device.status_on,
        "energy_calculated_kwh": round(energy_calculated, 6),
        "accumulated_energy_kwh": round(device.accumulated_energy_kwh, 4)
    }


@router.get("/energy/today")
async def get_energy_today(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get today's energy summary for user's house."""
    house_id = current_user.get("house_id")
    
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")
    
    device_repo = DeviceRepository(session)
    devices = await device_repo.get_by_house_id(house_id)
    
    # Calculate total accumulated energy
    total_consumed = sum(d.accumulated_energy_kwh for d in devices)
    
    # Estimate production (simplified - would come from simulation in real system)
    house_repo = HouseRepository(session)
    house = await house_repo.get_by_id(house_id)
    
    # Simplified estimates
    estimated_production = house.pv_capacity_kw * 5  # ~5 peak sun hours
    from_grid = max(0, total_consumed - estimated_production * 0.7)
    to_grid = max(0, estimated_production * 0.3)
    
    # Savings calculation (simplified)
    grid_price = 1.0  # lei/kWh
    savings = to_grid * grid_price * 0.8  # 80% of grid price for export
    
    return {
        "consumed_kwh": round(total_consumed, 2),
        "produced_kwh": round(estimated_production, 2),
        "from_grid_kwh": round(from_grid, 2),
        "to_grid_kwh": round(to_grid, 2),
        "savings_lei": round(savings, 2)
    }


@router.get("/energy/history")
async def get_energy_history(
    days: int = 7,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get energy history for user's house."""
    house_id = current_user.get("house_id")
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")

    house_repo = HouseRepository(session)
    house = await house_repo.get_by_id_with_relations(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    history = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        pts = _generate_energy_points(
            house,
            datetime(date.year, date.month, date.day, 0, 0),
            datetime(date.year, date.month, date.day, 23, 59),
            60
        )
        consumed = round(sum(p["consumption"] for p in pts), 2)
        produced = round(sum(p["solar"] for p in pts), 2)
        history.append({
            "date": date.strftime("%Y-%m-%d"),
            "consumed_kwh": consumed,
            "produced_kwh": produced,
        })
    return history


# ============================================================
# SETTINGS ENDPOINTS
# ============================================================

@router.get("/settings")
async def get_my_settings(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get current house settings (mode and backup reserve)."""
    house_id = current_user.get("house_id")
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")

    house_repo = HouseRepository(session)
    house = await house_repo.get_by_id_with_relations(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    backup_reserve_percent = 20.0
    if house.battery:
        backup_reserve_percent = round(
            (house.battery.soc_min_kwh / house.battery.capacity_kwh) * 100, 1
        )

    return {
        "mode": house.mode,
        "backup_reserve_percent": backup_reserve_percent
    }


@router.put("/settings")
async def update_my_settings(
    settings: SettingsUpdate,
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Update house settings (mode and/or backup reserve)."""
    house_id = current_user.get("house_id")
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")

    house_repo = HouseRepository(session)
    house = await house_repo.get_by_id_with_relations(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    if settings.mode is not None:
        if settings.mode not in ("Eco", "Profit"):
            raise HTTPException(status_code=400, detail="Mode must be 'Eco' or 'Profit'")
        house.mode = settings.mode
        try:
            from app.api.state import vpp_state
            if vpp_state.vpp:
                mem_house = vpp_state.vpp.get_house(house_id)
                if mem_house:
                    mem_house.mode = settings.mode
        except Exception as e:
            logger.warning(f"Failed to sync mode to VPP state: {e}")

    if settings.backup_reserve_percent is not None:
        percent = max(0.0, min(60.0, settings.backup_reserve_percent))
        if house.battery:
            house.battery.soc_min_kwh = round(house.battery.capacity_kwh * percent / 100, 2)
            try:
                from app.api.state import vpp_state
                if vpp_state.vpp:
                    mem_house = vpp_state.vpp.get_house(house_id)
                    if mem_house and mem_house.battery:
                        mem_house.battery.soc_min_kwh = house.battery.soc_min_kwh
            except Exception as e:
                logger.warning(f"Failed to sync battery config to VPP state: {e}")

    await session.flush()

    backup_reserve_percent = 20.0
    if house.battery:
        backup_reserve_percent = round(
            (house.battery.soc_min_kwh / house.battery.capacity_kwh) * 100, 1
        )

    return {
        "mode": house.mode,
        "backup_reserve_percent": backup_reserve_percent,
        "message": "Settings updated successfully"
    }


# ============================================================
# ENERGY CHART ENDPOINTS
# ============================================================

def _generate_energy_points(house, start_dt: datetime, end_dt: datetime, interval_min: int) -> list:
    """Generate realistic hourly energy data for a house based on its actual parameters."""
    pv_kw = house.pv_capacity_kw
    devices = house.devices or []

    base_load_kw = sum(d.power_w for d in devices if d.critical) / 1000
    max_load_kw = sum(d.power_w for d in devices) / 1000
    if max_load_kw < 0.1:
        max_load_kw = 3.0
    if base_load_kw < 0.05:
        base_load_kw = 0.2

    has_battery = house.battery is not None
    batt_cap = house.battery.capacity_kwh if has_battery else 0.0
    batt_min = house.battery.soc_min_kwh if has_battery else 0.0
    batt_ch_max = house.battery.p_ch_max_kw if has_battery else 0.0
    batt_dis_max = house.battery.p_dis_max_kw if has_battery else 0.0

    soc = batt_cap * 0.5
    dt_h = interval_min / 60.0
    points = []
    current = start_dt

    while current <= end_dt:
        h = current.hour
        m = current.minute

        # Solar: bell curve between 6AM and 8PM
        solar = 0.0
        if 6 <= h <= 20:
            solar_h = (h - 6) + m / 60.0
            solar = _math.sin((solar_h / 14.0) * _math.pi) * pv_kw * 0.8
            solar = max(0.0, solar)

        # Consumption profile by time of day
        if h < 6:
            load_factor = 0.10
        elif h < 9:
            load_factor = 0.45
        elif h < 17:
            load_factor = 0.25
        elif h < 22:
            load_factor = 0.75
        else:
            load_factor = 0.15
        consumption = base_load_kw + (max_load_kw - base_load_kw) * load_factor

        # Energy flows
        solar_to_load = min(solar, consumption)
        surplus = max(0.0, solar - consumption)
        deficit = max(0.0, consumption - solar)

        solar_to_battery = 0.0
        battery_to_load = 0.0

        if surplus > 0 and has_battery:
            space = min(batt_cap - soc, batt_ch_max * dt_h)
            solar_to_battery = min(surplus * dt_h, max(0.0, space))
            soc = min(batt_cap, soc + solar_to_battery)
            solar_to_battery = solar_to_battery / dt_h  # back to kW

        if deficit > 0 and has_battery:
            avail = min(soc - batt_min, batt_dis_max * dt_h)
            battery_to_load_kwh = min(deficit * dt_h, max(0.0, avail))
            battery_to_load = battery_to_load_kwh / dt_h  # kW
            soc = max(batt_min, soc - battery_to_load_kwh)

        solar_to_grid = max(0.0, surplus - solar_to_battery)
        grid_to_load = max(0.0, deficit - battery_to_load)

        points.append({
            "timestamp": current.isoformat(),
            "solar": round(solar, 3),
            "consumption": round(consumption, 3),
            "battery": round(solar_to_battery - battery_to_load, 3),
            "grid": round(grid_to_load - solar_to_grid, 3),
            "solar_to_load": round(solar_to_load, 3),
            "solar_to_battery": round(solar_to_battery, 3),
            "solar_to_grid": round(solar_to_grid, 3),
            "battery_to_load": round(battery_to_load, 3),
            "grid_to_load": round(grid_to_load, 3),
        })

        current += timedelta(minutes=interval_min)

    return points


@router.get("/energy/chart")
async def get_energy_chart(
    period: str = Query("day", description="Time period: day, week, month"),
    date: Optional[str] = Query(None, description="Reference date YYYY-MM-DD (defaults to today)"),
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get energy chart data for user's house (solar/consumption/battery/grid over time)."""
    house_id = current_user.get("house_id")
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")

    house_repo = HouseRepository(session)
    house = await house_repo.get_by_id_with_relations(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    now = datetime.now()
    if date:
        try:
            ref = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        ref = now

    if period == "day":
        start = datetime(ref.year, ref.month, ref.day, 0, 0)
        end = now if ref.date() == now.date() else datetime(ref.year, ref.month, ref.day, 23, 59)
        interval_min = 10
    elif period == "week":
        weekday = ref.weekday()
        start = datetime(ref.year, ref.month, ref.day, 0, 0) - timedelta(days=weekday)
        end = min(ref.replace(hour=23, minute=59), now)
        interval_min = 60
    elif period == "month":
        start = datetime(ref.year, ref.month, 1, 0, 0)
        end = min(ref.replace(hour=23, minute=59), now)
        interval_min = 240
    else:
        raise HTTPException(status_code=400, detail="Invalid period. Use: day, week, month")

    if start > end:
        end = start + timedelta(minutes=interval_min)

    data_points = _generate_energy_points(house, start, end, interval_min)

    return {
        "period": period,
        "date": ref.strftime("%Y-%m-%d"),
        "interval_minutes": interval_min,
        "data_points": data_points
    }


@router.get("/energy/impact")
async def get_energy_impact(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get energy impact data: source distribution, peak/off-peak, monthly savings."""
    house_id = current_user.get("house_id")
    if not house_id:
        raise HTTPException(status_code=403, detail="No house assigned to this user")

    house_repo = HouseRepository(session)
    house = await house_repo.get_by_id_with_relations(house_id)
    if not house:
        raise HTTPException(status_code=404, detail="House not found")

    now = datetime.now()
    start = datetime(now.year, now.month, now.day, 0, 0)
    pts = _generate_energy_points(house, start, now, 60)

    from_solar = sum(p["solar_to_load"] for p in pts)
    from_battery = sum(p["battery_to_load"] for p in pts)
    from_grid = sum(p["grid_to_load"] for p in pts)
    total = from_solar + from_battery + from_grid or 1.0

    solar_pct = round(from_solar / total * 100, 1)
    battery_pct = round(from_battery / total * 100, 1)
    grid_pct = round(100.0 - solar_pct - battery_pct, 1)

    peak_pts = [p for p in pts if 17 <= datetime.fromisoformat(p["timestamp"]).hour < 22]
    off_peak_pts = [p for p in pts if not (17 <= datetime.fromisoformat(p["timestamp"]).hour < 22)]

    def _sum(lst, key):
        return round(sum(p[key] for p in lst), 2)

    peak = {"solar": _sum(peak_pts, "solar_to_load"), "battery": _sum(peak_pts, "battery_to_load"), "grid": _sum(peak_pts, "grid_to_load")}
    off_peak = {"solar": _sum(off_peak_pts, "solar_to_load"), "battery": _sum(off_peak_pts, "battery_to_load"), "grid": _sum(off_peak_pts, "grid_to_load")}

    # Monthly savings: credits from wallet, last 6 months
    month_names = ["Ian", "Feb", "Mar", "Apr", "Mai", "Iun", "Iul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    monthly_savings = []

    try:
        from app.db.models import WalletModel, WalletTransactionModel
        six_ago = now - timedelta(days=180)
        stmt = (
            select(WalletTransactionModel.created_at, WalletTransactionModel.amount_lei)
            .join(WalletModel, WalletTransactionModel.wallet_id == WalletModel.id)
            .where(
                WalletModel.house_id == house_id,
                WalletTransactionModel.transaction_type == "credit",
                WalletTransactionModel.created_at >= six_ago
            )
        )
        rows = (await session.execute(stmt)).all()
        savings_map: dict = defaultdict(float)
        for row in rows:
            savings_map[(row.created_at.year, row.created_at.month)] += float(row.amount_lei)
    except Exception as e:
        logger.warning(f"Could not load wallet savings: {e}")
        savings_map = {}

    pv = house.pv_capacity_kw
    for i in range(5, -1, -1):
        offset = now.month - i - 1
        m = offset % 12 + 1
        y = now.year + (offset // 12)
        savings = savings_map.get((y, m))
        if savings is None:
            savings = round(pv * (8 + i * 4), 2)
        monthly_savings.append({
            "month": month_names[m - 1],
            "savings": round(savings, 2),
            "current": (m == now.month and y == now.year),
        })

    return {
        "solar_percent": solar_pct,
        "battery_percent": battery_pct,
        "grid_percent": grid_pct,
        "solar_kwh": round(from_solar, 2),
        "battery_kwh": round(from_battery, 2),
        "grid_kwh": round(from_grid, 2),
        "peak": peak,
        "off_peak": off_peak,
        "monthly_savings": monthly_savings,
    }
