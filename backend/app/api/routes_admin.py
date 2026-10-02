from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_ws_user, require_admin
from app.api.schemas import CreateUserRequest, ManualTradeRequest, UpdateUserRequest
from app.db.database import get_session
from app.db.models import UserModel
from app.db.repositories import UserRepository
from app.services import users
from app.services.serializers import trade_dict, user_dict
from app.services.settlement import SettlementError, SettlementService, Trade
from app.services.simulation_loop import sim

router = APIRouter(prefix="/admin", tags=["admin"])


async def _user_or_404(session: AsyncSession, user_id: str) -> UserModel:
    user = await UserRepository(session).get_with_house(user_id)
    if user is None:
        raise HTTPException(404, "Utilizatorul nu exista")
    return user


@router.get("/users")
async def list_users(_: UserModel = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return [user_dict(u) for u in await UserRepository(session).get_all_with_houses()]


@router.post("/users", status_code=201)
async def add_user(body: CreateUserRequest, _: UserModel = Depends(require_admin),
                   session: AsyncSession = Depends(get_session)):
    if body.house_id is not None:
        await users.ensure_house_assignable(session, body.house_id)
    user = await users.create_user(session, body.username, body.password, body.house_id, body.is_admin)
    if user is None:
        raise HTTPException(400, "Numele de utilizator exista deja")
    return user_dict(await _user_or_404(session, user.id))


@router.get("/users/{user_id}")
async def get_user(user_id: str, _: UserModel = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return user_dict(await _user_or_404(session, user_id))


@router.put("/users/{user_id}")
async def update_user(user_id: str, body: UpdateUserRequest, _: UserModel = Depends(require_admin),
                      session: AsyncSession = Depends(get_session)):
    user = await _user_or_404(session, user_id)
    await users.update_user(session, user, body.password, body.house_id, body.is_admin)
    return user_dict(await _user_or_404(session, user_id))


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: UserModel = Depends(require_admin),
                      session: AsyncSession = Depends(get_session)):
    if user_id == admin.id:
        raise HTTPException(400, "Nu iti poti sterge propriul cont")
    await _user_or_404(session, user_id)
    await UserRepository(session).delete(user_id)
    return {"deleted": True, "user_id": user_id}


@router.post("/trades", status_code=201)
async def manual_trade(body: ManualTradeRequest, _: UserModel = Depends(require_admin),
                       session: AsyncSession = Depends(get_session)):
    grid_price = sim.current_prices()[0] if sim.scenario is not None else body.price_lei_kwh
    trade = Trade(body.seller_house_id, body.buyer_house_id, body.energy_kwh, body.price_lei_kwh, grid_price)
    try:
        record = await SettlementService(session).settle_trade(trade, sim.sim_datetime)
    except SettlementError as e:
        raise HTTPException(400, str(e)) from None
    return trade_dict(record)


@router.websocket("/ws")
async def live_updates(websocket: WebSocket, user: UserModel | None = Depends(get_ws_user)):
    """One {"type": "connected", ...} message, then one "step" message per simulation step."""
    await websocket.accept()
    if user is None:
        # closing before accept makes the server answer the handshake with HTTP 403, which a browser
        # only reports as code 1006; after accept the client sees 1008 and knows the token is the problem
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token invalid sau lipsa")
        return
    sim.add_ws(websocket)
    try:
        await websocket.send_json({"type": "connected", "status": sim.status(), "last": sim.last_result})
        while True:
            text = await websocket.receive_text()
            if text == "ping":
                await websocket.send_text("pong")
            elif text == "status":
                await websocket.send_json({"type": "status", "status": sim.status()})
    except WebSocketDisconnect:
        pass
    finally:
        sim.remove_ws(websocket)
