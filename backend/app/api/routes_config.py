from dataclasses import replace

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, require_admin
from app.api.schemas import ConfigUpdate
from app.db.models import UserModel
from app.services.simulation_loop import CONTROLLER_NAMES, SimConfig, sim

router = APIRouter(prefix="/config", tags=["config"])


def _config_response() -> dict:
    return {**sim.config.to_dict(), "dt_hours": sim.dt_h, "data_source": sim.data_source, "data_year": sim.data_year,
            "controllers": list(CONTROLLER_NAMES)}


@router.get("")
async def get_config(_: UserModel = Depends(get_current_user)):
    return _config_response()


@router.put("")
async def update_config(body: ConfigUpdate, _: UserModel = Depends(require_admin)):
    changes = body.model_dump(exclude_none=True)
    if not changes:
        raise HTTPException(400, "Nimic de modificat")
    try:
        await sim.apply_config(replace(sim.config, **changes))
    except ValueError as e:
        raise HTTPException(400, str(e)) from None
    return {"message": f"Configuratie actualizata ({', '.join(changes)})", "updated_fields": list(changes),
            "config": _config_response()}


@router.post("/reset")
async def reset_config(_: UserModel = Depends(require_admin)):
    await sim.apply_config(SimConfig.from_settings())
    return {"message": "Configuratie readusa la valorile implicite", "config": _config_response()}
