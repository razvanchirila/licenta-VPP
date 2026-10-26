from fastapi import APIRouter, Depends, HTTPException, Response, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_ws_user, require_admin
from app.api.schemas import CreateUserRequest, HouseSpecRequest, ManualTradeRequest, UpdateUserRequest
from app.db.database import get_session
from app.db.models import UserModel
from app.db.repositories import HouseRepository, UserRepository
from app.services import neighbourhood, users
from app.services.serializers import trade_dict, user_dict
from app.services.settlement import SettlementError, SettlementService, Trade
from app.services.simulation_loop import sim
from vpp_core.load_model import HouseSpec, load_catalog

router = APIRouter(prefix="/admin", tags=["admin"])


async def _user_or_404(session: AsyncSession, user_id: str) -> UserModel:
    user = await UserRepository(session).get_with_house(user_id)
    if user is None:
        raise HTTPException(404, "Utilizatorul nu exista")
    return user


@router.get("/neighbourhood")
async def get_neighbourhood(_: UserModel = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    catalog = load_catalog()
    houses = await HouseRepository(session).get_all_with_relations()
    return {"catalog": neighbourhood.catalog_view(catalog),
            "houses": [neighbourhood.spec_dict(neighbourhood.spec_of(h, catalog)) for h in houses]}


@router.put("/neighbourhood/{house_id}")
async def update_house_spec(house_id: int, body: HouseSpecRequest, _: UserModel = Depends(require_admin),
                            session: AsyncSession = Depends(get_session)):
    house = await HouseRepository(session).get_by_id_with_relations(house_id)
    if house is None:
        raise HTTPException(404, "Casa nu exista")
    spec = HouseSpec(house_id, body.description.strip(), body.people, body.home_daytime, body.heating.lower(),
                     body.insulation.lower(), tuple(dict.fromkeys(name.lower() for name in body.devices)))
    catalog = load_catalog()
    try:
        await neighbourhood.apply_spec(session, house, spec, catalog)
    except ValueError as error:
        raise HTTPException(400, str(error)) from None
    await session.refresh(house, ["devices"])
    return neighbourhood.spec_dict(neighbourhood.spec_of(house, catalog))


@router.post("/neighbourhood/reset")
async def reset_neighbourhood(_: UserModel = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    await neighbourhood.reset_all(session, await HouseRepository(session).get_all_with_relations())
    return {"message": "Cartierul a revenit la case.csv"}


@router.get("/neighbourhood/export")
async def export_neighbourhood(_: UserModel = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    text = neighbourhood.export_csv(await HouseRepository(session).get_all_with_relations())
    return Response(text, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="case.csv"'})


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
