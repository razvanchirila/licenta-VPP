"""Admin routes for user management."""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.db.repositories import UserRepository, HouseRepository
from app.services.auth import AuthService

router = APIRouter(prefix="/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    house_id: Optional[int] = None
    is_admin: bool = False


class UpdateUserRequest(BaseModel):
    password: Optional[str] = None
    house_id: Optional[int] = None
    is_admin: Optional[bool] = None


@router.post("/users")
async def create_user(
    request: CreateUserRequest,
    session: AsyncSession = Depends(get_session)
):
    """Create a new user with optional house assignment."""
    user_repo = UserRepository(session)
    house_repo = HouseRepository(session)
    
    # Check username uniqueness
    existing = await user_repo.get_by_username(request.username)
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Validate house if provided
    if request.house_id:
        house = await house_repo.get_by_id(request.house_id)
        if not house:
            raise HTTPException(status_code=400, detail=f"House {request.house_id} not found")
        
        # Check if house is already assigned
        if await user_repo.is_house_assigned(request.house_id):
            raise HTTPException(status_code=400, detail=f"House {request.house_id} is already assigned to another user")
    
    # Create user
    password_hash = AuthService.hash_password(request.password)
    user = await user_repo.create_user(
        username=request.username,
        password_hash=password_hash,
        house_id=request.house_id,
        is_admin=request.is_admin
    )
    
    return {
        "user_id": user.id,
        "username": user.username,
        "house_id": user.house_id,
        "is_admin": user.is_admin
    }


@router.get("/users")
async def list_users(session: AsyncSession = Depends(get_session)):
    """List all users with their assigned houses."""
    user_repo = UserRepository(session)
    users = await user_repo.get_all_with_houses()
    
    return [
        {
            "user_id": u.id,
            "username": u.username,
            "house_id": u.house_id,
            "house_name": u.house.name if u.house else None,
            "is_admin": u.is_admin,
            "created_at": u.created_at.isoformat() if u.created_at else None
        }
        for u in users
    ]


@router.get("/users/{user_id}")
async def get_user(user_id: str, session: AsyncSession = Depends(get_session)):
    """Get a specific user."""
    user_repo = UserRepository(session)
    user = await user_repo.get_with_house(user_id)
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "house_id": user.house_id,
        "house_name": user.house.name if user.house else None,
        "is_admin": user.is_admin,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    session: AsyncSession = Depends(get_session)
):
    """Update user details."""
    user_repo = UserRepository(session)
    house_repo = HouseRepository(session)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update password if provided
    if request.password:
        user.password_hash = AuthService.hash_password(request.password)
    
    # Update house if provided
    if request.house_id is not None:
        if request.house_id != 0:  # 0 means unassign
            house = await house_repo.get_by_id(request.house_id)
            if not house:
                raise HTTPException(status_code=400, detail=f"House {request.house_id} not found")
            
            if await user_repo.is_house_assigned(request.house_id, exclude_user_id=user_id):
                raise HTTPException(status_code=400, detail=f"House {request.house_id} is already assigned")
            
            user.house_id = request.house_id
        else:
            user.house_id = None
    
    # Update admin status if provided
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    
    await session.flush()
    await session.refresh(user)
    
    return {
        "user_id": user.id,
        "username": user.username,
        "house_id": user.house_id,
        "is_admin": user.is_admin,
        "updated": True
    }


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, session: AsyncSession = Depends(get_session)):
    """Delete a user."""
    user_repo = UserRepository(session)
    
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await user_repo.delete(user_id)
    
    return {"deleted": True, "user_id": user_id}



# WebSocket and Simulation Control endpoints
from fastapi import WebSocket, WebSocketDisconnect
from app.services import simulation_loop


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live simulation updates."""
    await websocket.accept()
    simulation_loop.add_websocket_client(websocket)
    
    try:
        # Send initial status
        await websocket.send_json({
            "type": "connected",
            "status": simulation_loop.get_status()
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                # Handle ping/pong or commands
                if data == "ping":
                    await websocket.send_text("pong")
                elif data == "status":
                    await websocket.send_json({
                        "type": "status",
                        "status": simulation_loop.get_status()
                    })
            except WebSocketDisconnect:
                break
    finally:
        simulation_loop.remove_websocket_client(websocket)


@router.get("/simulation/status")
async def get_simulation_status():
    """Get current simulation status."""
    return simulation_loop.get_status()


@router.post("/simulation/pause")
async def pause_simulation():
    """Pause the simulation loop."""
    simulation_loop.pause()
    return {"message": "Simulation paused", "status": simulation_loop.get_status()}


@router.post("/simulation/resume")
async def resume_simulation():
    """Resume the simulation loop."""
    simulation_loop.resume()
    return {"message": "Simulation resumed", "status": simulation_loop.get_status()}


@router.post("/simulation/speed")
async def set_simulation_speed(seconds: float = 5.0):
    """Change simulation speed (interval between steps)."""
    simulation_loop.set_speed(seconds)
    return {"message": f"Speed set to {simulation_loop.interval_seconds}s", "status": simulation_loop.get_status()}


@router.post("/simulation/step")
async def manual_step():
    """Execute a single simulation step manually."""
    result = await simulation_loop.execute_step()
    if result:
        return {"message": "Step executed", "result": result}
    return {"message": "Step failed - VPP may not be initialized"}


@router.post("/reload")
async def reload_vpp_from_db():
    """
    Reload VPP state from database.
    
    Use this after making direct changes to the database (MySQL queries)
    to sync the in-memory VPP state with the database.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from app.api.state import vpp_state
    from app.models.vpp import VPP
    from app.models.house import House
    from app.models.battery import Battery
    from app.models.device import Device
    from app.db.database import get_session_context
    from app.db.repositories import HouseRepository
    
    try:
        async with get_session_context() as session:
            house_repo = HouseRepository(session)
            db_houses = await house_repo.get_all_with_relations()
            
            if not db_houses:
                return {"error": "No houses in database"}
            
            # Create new VPP from DB data
            vpp = VPP()
            
            for db_house in db_houses:
                # Create Battery if exists
                battery = None
                if db_house.battery:
                    battery = Battery(
                        capacity_kwh=db_house.battery.capacity_kwh,
                        soc_min_ratio=db_house.battery.soc_min_kwh / db_house.battery.capacity_kwh,
                        p_ch_max_kw=db_house.battery.p_ch_max_kw,
                        p_dis_max_kw=db_house.battery.p_dis_max_kw,
                        initial_soc_ratio=1.0
                    )
                    # Set actual SOC from DB
                    battery.soc_kwh = db_house.battery.soc_kwh
                
                # Create House
                house = House(
                    id=db_house.id,
                    battery=battery,
                    mode=db_house.mode,
                    has_pv=db_house.has_pv,
                    pv_capacity_kw=db_house.pv_capacity_kw
                )
                
                # Add devices
                for db_device in db_house.devices:
                    device = Device(
                        id=db_device.id,
                        name=db_device.name,
                        power_w=db_device.power_w,
                        critical=db_device.critical,
                        status_on=db_device.status_on,
                        last_state_change_ts=db_device.last_state_change_ts,
                        accumulated_energy_kwh=db_device.accumulated_energy_kwh
                    )
                    house.add_device(device)
                
                vpp.add_house(house)
            
            # Update global state
            vpp_state.vpp = vpp
            
            logger.info(f"Reloaded {len(db_houses)} houses from database")
            
            return {
                "message": "VPP state reloaded from database",
                "houses_loaded": len(db_houses),
                "total_devices": sum(len(h.devices) for h in vpp.houses),
                "houses": [
                    {
                        "id": h.id,
                        "devices": len(h.devices),
                        "battery_soc": h.battery.get_soc_percent() if h.battery else None
                    }
                    for h in vpp.houses
                ]
            }
    except Exception as e:
        logger.error(f"Failed to reload VPP: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
