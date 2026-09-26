import logging
from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_user, require_admin
from app.api.schemas import SpeedRequest
from app.db.models import UserModel
from app.services.simulation_loop import sim

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/sim", tags=["simulation"])


@router.get("/status")
async def status(_: UserModel = Depends(get_current_user)):
    return sim.status()


@router.get("/prices")
async def prices(_: UserModel = Depends(get_current_user)):
    return {"date": sim.day.isoformat(), "dt_hours": sim.dt_h, "current_step": sim.t, "prices": sim.prices_today()}


@router.get("/history")
async def history(limit: int = Query(96, ge=1, le=600), _: UserModel = Depends(get_current_user)):
    items = list(sim.history)[-limit:]
    return {"count": len(items), "steps": items}


@router.post("/start")
async def start(_: UserModel = Depends(require_admin)):
    await sim.start()
    return {"message": "Simulare pornita", "status": sim.status()}


@router.post("/stop")
async def stop(_: UserModel = Depends(require_admin)):
    await sim.stop()
    return {"message": "Simulare oprita", "status": sim.status()}


@router.post("/pause")
async def pause(_: UserModel = Depends(require_admin)):
    sim.paused = True
    return {"message": "Simulare in pauza", "paused": True, "status": sim.status()}


@router.post("/resume")
async def resume(_: UserModel = Depends(require_admin)):
    sim.paused = False
    sim.last_error = None
    return {"message": "Simulare reluata", "paused": False, "status": sim.status()}


@router.post("/speed")
async def speed(body: SpeedRequest, _: UserModel = Depends(require_admin)):
    await sim.apply_config(replace(sim.config, tick_seconds=body.tick_seconds))
    return {"message": f"Un pas la {body.tick_seconds} s", "tick_seconds": body.tick_seconds}


@router.post("/step")
async def step(_: UserModel = Depends(require_admin)):
    try:
        result = await sim.step()
    except Exception as e:
        logger.exception("Manual simulation step failed")
        raise HTTPException(500, f"Pasul de simulare a esuat: {e}") from None
    await sim.broadcast(result)
    return result


@router.post("/reset")
async def reset(_: UserModel = Depends(require_admin)):
    await sim.reset()
    return {"message": "Simulare resetata", "status": sim.status()}
