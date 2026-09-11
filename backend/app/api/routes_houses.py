"""
Houses API routes - syncs with both memory (VPP state) and database.
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.repositories import HouseRepository, DeviceRepository

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/houses", tags=["houses"])


# Pydantic models for requests
class ModeChangeRequest(BaseModel):
    mode: str  # "Eco" or "Profit"


class DeviceCreate(BaseModel):
    name: str
    power_w: float
    critical: bool = False
    status_on: bool = False


class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    power_w: Optional[float] = None
    critical: Optional[bool] = None
    status_on: Optional[bool] = None


@router.get("/")
def get_all_houses():
    """Get all houses in the VPP"""
    from app.api.state import vpp_state
    
    if not vpp_state.vpp:
        return []
    
    return [house.to_dict() for house in vpp_state.vpp.houses]


@router.get("/{house_id}")
def get_house(house_id: int):
    """Get specific house by ID"""
    from app.api.state import vpp_state
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    house = vpp_state.vpp.get_house(house_id)
    if not house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    return house.to_dict()


@router.post("/{house_id}/mode")
async def change_house_mode(
    house_id: int,
    request: ModeChangeRequest,
    session: AsyncSession = Depends(get_session)
):
    """Change house operating mode (Eco/Profit) - saves to DB"""
    from app.api.state import vpp_state
    
    if request.mode not in ["Eco", "Profit"]:
        raise HTTPException(status_code=400, detail="Mode must be 'Eco' or 'Profit'")
    
    # Update in database
    house_repo = HouseRepository(session)
    db_house = await house_repo.get_by_id(house_id)
    
    if not db_house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    db_house.mode = request.mode
    await session.flush()
    
    # Update in memory
    if vpp_state.vpp:
        mem_house = vpp_state.vpp.get_house(house_id)
        if mem_house:
            mem_house.mode = request.mode
    
    logger.info(f"House {house_id} mode changed to {request.mode}")
    
    return {
        "house_id": house_id,
        "mode": request.mode,
        "message": f"Mode changed to {request.mode}"
    }


@router.get("/{house_id}/devices")
def get_house_devices(house_id: int):
    """Get all devices in a house"""
    from app.api.state import vpp_state
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    house = vpp_state.vpp.get_house(house_id)
    if not house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    return [device.to_dict() for device in house.devices]


@router.post("/{house_id}/devices")
async def add_device(
    house_id: int,
    device: DeviceCreate,
    session: AsyncSession = Depends(get_session)
):
    """Add a new device to a house - saves to DB"""
    from app.api.state import vpp_state
    from app.models.device import Device as MemDevice
    from app.db.models import DeviceModel
    
    # Validate
    if device.power_w <= 0:
        raise HTTPException(status_code=400, detail="Power must be positive")
    if device.power_w > 50000:
        raise HTTPException(status_code=400, detail="Power exceeds maximum (50kW)")
    
    # Check house exists
    house_repo = HouseRepository(session)
    db_house = await house_repo.get_by_id(house_id)
    if not db_house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    # Use simulation time, not real time
    from app.services.simulation_loop import simulation_loop
    current_time = simulation_loop.clock.sim_datetime
    
    # Create in database
    db_device = DeviceModel(
        house_id=house_id,
        name=device.name,
        power_w=device.power_w,
        critical=device.critical,
        status_on=device.status_on,
        accumulated_energy_kwh=0.0,
        last_state_change_ts=current_time if device.status_on else None
    )
    session.add(db_device)
    await session.flush()
    await session.refresh(db_device)
    
    # Add to memory
    if vpp_state.vpp:
        mem_house = vpp_state.vpp.get_house(house_id)
        if mem_house:
            mem_device = MemDevice(
                id=db_device.id,
                name=db_device.name,
                power_w=db_device.power_w,
                critical=db_device.critical,
                status_on=db_device.status_on,
                last_state_change_ts=db_device.last_state_change_ts,
                accumulated_energy_kwh=0.0
            )
            mem_house.add_device(mem_device)
    
    logger.info(f"Added device {db_device.id} to house {house_id}")
    
    return {
        "id": db_device.id,
        "name": db_device.name,
        "power_w": db_device.power_w,
        "critical": db_device.critical,
        "status_on": db_device.status_on,
        "message": "Device created successfully"
    }


@router.post("/{house_id}/devices/{device_id}/toggle")
async def toggle_device(
    house_id: int,
    device_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Toggle device on/off - saves to DB"""
    from app.api.state import vpp_state
    from app.db.repositories.energy_log_repository import EnergyLogRepository
    import json
    
    device_repo = DeviceRepository(session)
    db_device = await device_repo.get_by_id(device_id)
    
    if not db_device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    if db_device.house_id != house_id:
        raise HTTPException(status_code=403, detail="Device does not belong to this house")
    
    if db_device.critical and db_device.status_on:
        raise HTTPException(status_code=400, detail="Cannot turn off critical device")
    
    # Use simulation time, not real time
    from app.services.simulation_loop import simulation_loop
    current_time = simulation_loop.clock.sim_datetime
    
    # Calculate energy if turning OFF
    energy_calculated = 0.0
    was_on = db_device.status_on
    duration_hours = 0.0
    
    if db_device.status_on and db_device.last_state_change_ts:
        duration = current_time - db_device.last_state_change_ts
        duration_hours = duration.total_seconds() / 3600
        power_kw = db_device.power_w / 1000
        energy_calculated = power_kw * duration_hours
        db_device.accumulated_energy_kwh += energy_calculated
    
    # Toggle in DB
    db_device.status_on = not db_device.status_on
    db_device.last_state_change_ts = current_time
    await session.flush()
    
    # Log to energy_logs table for analytics
    energy_log_repo = EnergyLogRepository(session)
    
    if was_on:
        # Device turned OFF - log energy consumed
        details = json.dumps({
            "duration_hours": round(duration_hours, 4),
            "power_w": db_device.power_w,
            "triggered_by": "admin"
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
            "power_w": db_device.power_w,
            "triggered_by": "admin"
        })
        await energy_log_repo.log_toggle_on(
            device_id=device_id,
            details=details
        )
        logger.info(f"Logged toggle_on for device {device_id}")
    
    # Sync to memory
    if vpp_state.vpp:
        mem_house = vpp_state.vpp.get_house(house_id)
        if mem_house:
            mem_device = mem_house.get_device(device_id)
            if mem_device:
                mem_device.status_on = db_device.status_on
                mem_device.last_state_change_ts = db_device.last_state_change_ts
                mem_device.accumulated_energy_kwh = db_device.accumulated_energy_kwh
    
    logger.info(f"Toggled device {device_id} to {'ON' if db_device.status_on else 'OFF'}")
    
    return {
        "id": db_device.id,
        "name": db_device.name,
        "status_on": db_device.status_on,
        "energy_calculated_kwh": round(energy_calculated, 6)
    }


@router.put("/{house_id}/devices/{device_id}")
async def update_device(
    house_id: int,
    device_id: int,
    device_update: DeviceUpdate,
    session: AsyncSession = Depends(get_session)
):
    """Update device properties - saves to DB"""
    from app.api.state import vpp_state
    from app.db.repositories.energy_log_repository import EnergyLogRepository
    from app.db.models import EnergyLogModel
    import json
    
    device_repo = DeviceRepository(session)
    db_device = await device_repo.get_by_id(device_id)
    
    if not db_device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    if db_device.house_id != house_id:
        raise HTTPException(status_code=403, detail="Device does not belong to this house")
    
    from app.services.simulation_loop import simulation_loop
    current_time = simulation_loop.clock.sim_datetime
    
    # Track old values for logging
    old_power = db_device.power_w
    old_critical = db_device.critical
    
    # Update in DB
    if device_update.name is not None:
        db_device.name = device_update.name
    
    # If changing power on an ON device, calculate energy with old power first
    if device_update.power_w is not None:
        if device_update.power_w <= 0:
            raise HTTPException(status_code=400, detail="Power must be positive")
        
        # If device is ON and power is changing, settle energy with old power
        if db_device.status_on and db_device.last_state_change_ts:
            duration = current_time - db_device.last_state_change_ts
            duration_hours = duration.total_seconds() / 3600
            old_power_kw = db_device.power_w / 1000
            energy_with_old_power = old_power_kw * duration_hours
            db_device.accumulated_energy_kwh += energy_with_old_power
            db_device.last_state_change_ts = current_time  # Reset for new power
        
        db_device.power_w = device_update.power_w
    
    if device_update.critical is not None:
        db_device.critical = device_update.critical
    
    # If changing status_on, handle energy calculation
    if device_update.status_on is not None and device_update.status_on != db_device.status_on:
        if db_device.status_on and db_device.last_state_change_ts:
            # Turning OFF - calculate energy
            duration = current_time - db_device.last_state_change_ts
            duration_hours = duration.total_seconds() / 3600
            power_kw = db_device.power_w / 1000
            db_device.accumulated_energy_kwh += power_kw * duration_hours
        
        db_device.status_on = device_update.status_on
        db_device.last_state_change_ts = current_time if device_update.status_on else None
    
    await session.flush()
    
    # Log changes to energy_logs
    energy_log_repo = EnergyLogRepository(session)
    
    # Log power change
    if device_update.power_w is not None and old_power != db_device.power_w:
        details = json.dumps({
            "old_power_w": old_power,
            "new_power_w": db_device.power_w,
            "change_type": "power_change"
        })
        await energy_log_repo.create(EnergyLogModel(
            device_id=device_id,
            energy_kwh=0.0,
            event_type="power_change",
            details=details
        ))
        logger.info(f"Logged power_change for device {device_id}: {old_power}W -> {db_device.power_w}W")
    
    # Log critical status change
    if device_update.critical is not None and old_critical != db_device.critical:
        details = json.dumps({
            "old_critical": old_critical,
            "new_critical": db_device.critical,
            "change_type": "critical_change"
        })
        await energy_log_repo.create(EnergyLogModel(
            device_id=device_id,
            energy_kwh=0.0,
            event_type="critical_change",
            details=details
        ))
        logger.info(f"Logged critical_change for device {device_id}: {old_critical} -> {db_device.critical}")
    
    # Sync to memory
    if vpp_state.vpp:
        mem_house = vpp_state.vpp.get_house(house_id)
        if mem_house:
            mem_device = mem_house.get_device(device_id)
            if mem_device:
                mem_device.name = db_device.name
                mem_device.power_w = db_device.power_w
                mem_device.critical = db_device.critical
                mem_device.status_on = db_device.status_on
                mem_device.last_state_change_ts = db_device.last_state_change_ts
                mem_device.accumulated_energy_kwh = db_device.accumulated_energy_kwh
    
    logger.info(f"Updated device {device_id}")
    
    return {
        "id": db_device.id,
        "name": db_device.name,
        "power_w": db_device.power_w,
        "critical": db_device.critical,
        "status_on": db_device.status_on,
        "message": "Device updated successfully"
    }


@router.delete("/{house_id}/devices/{device_id}")
async def remove_device(
    house_id: int,
    device_id: int,
    session: AsyncSession = Depends(get_session)
):
    """Remove a device from a house - deletes from DB"""
    from app.api.state import vpp_state
    
    device_repo = DeviceRepository(session)
    db_device = await device_repo.get_by_id(device_id)
    
    if not db_device:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    
    if db_device.house_id != house_id:
        raise HTTPException(status_code=403, detail="Device does not belong to this house")
    
    if db_device.critical:
        raise HTTPException(status_code=400, detail="Cannot delete critical device")
    
    device_name = db_device.name
    await session.delete(db_device)
    await session.flush()
    
    # Remove from memory
    if vpp_state.vpp:
        mem_house = vpp_state.vpp.get_house(house_id)
        if mem_house:
            mem_house.remove_device(device_id)
    
    logger.info(f"Deleted device {device_id} from house {house_id}")
    
    return {"message": f"Device '{device_name}' removed successfully"}


@router.get("/{house_id}/battery")
def get_battery_status(house_id: int):
    """Get battery status for a house"""
    from app.api.state import vpp_state
    
    if not vpp_state.vpp:
        raise HTTPException(status_code=404, detail="VPP not initialized")
    
    house = vpp_state.vpp.get_house(house_id)
    if not house:
        raise HTTPException(status_code=404, detail=f"House {house_id} not found")
    
    if not house.battery:
        raise HTTPException(status_code=404, detail=f"House {house_id} has no battery")
    
    return house.battery.to_dict()
