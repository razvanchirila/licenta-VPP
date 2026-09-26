from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_session
from app.db.models import UserModel
from app.services import vpp
from app.services.simulation_loop import sim

router = APIRouter(prefix="/vpp", tags=["vpp"])


@router.get("/state")
async def state(_: UserModel = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await vpp.community_state(session, sim)


@router.get("/stats")
async def stats(_: UserModel = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return {**(await vpp.community_state(session, sim)), "today": await vpp.today_totals(session, sim.day)}
