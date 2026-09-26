from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import load_house, require_admin, require_house_access
from app.api.schemas import DeviceCreate, DeviceUpdate, ModeRequest
from app.db.database import get_session
from app.db.models import UserModel
from app.db.repositories import DeviceRepository, HouseRepository
from app.services import devices, houses
from app.services.serializers import battery_dict, device_dict, house_dict
from app.services.simulation_loop import sim

router = APIRouter(prefix="/houses", tags=["houses"])


def _actor(user: UserModel) -> str:
    return "admin" if user.is_admin else "user"


@router.get("")
async def list_houses(_: UserModel = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    rows = await HouseRepository(session).get_all_with_relations()
    return [house_dict(h, sim.house_last_step(h.id)) for h in rows]


@router.get("/{house_id}")
async def get_house(house_id: int, _: UserModel = Depends(require_house_access),
                    session: AsyncSession = Depends(get_session)):
    return house_dict(await load_house(session, house_id), sim.house_last_step(house_id))


@router.post("/{house_id}/mode")
async def set_mode(house_id: int, body: ModeRequest, _: UserModel = Depends(require_house_access),
                   session: AsyncSession = Depends(get_session)):
    house = await load_house(session, house_id)
    await houses.set_mode(session, house, body.mode)
    return {"house_id": house_id, "mode": house.mode, "message": f"Mod schimbat pe {house.mode}"}


@router.get("/{house_id}/battery")
async def get_battery(house_id: int, _: UserModel = Depends(require_house_access),
                      session: AsyncSession = Depends(get_session)):
    house = await load_house(session, house_id)
    if house.battery is None:
        raise HTTPException(404, f"Casa {house_id} nu are baterie")
    return battery_dict(house.battery, house.vpp_reserve.reserved_kwh if house.vpp_reserve else 0.0)


@router.get("/{house_id}/devices")
async def list_devices(house_id: int, _: UserModel = Depends(require_house_access),
                       session: AsyncSession = Depends(get_session)):
    await load_house(session, house_id)
    return [device_dict(d) for d in await DeviceRepository(session).get_by_house_id(house_id)]


@router.post("/{house_id}/devices", status_code=201)
async def add_device(house_id: int, body: DeviceCreate, _: UserModel = Depends(require_house_access),
                     session: AsyncSession = Depends(get_session)):
    await load_house(session, house_id)
    device = await devices.create_device(session, house_id, body, sim.sim_datetime)
    return device_dict(device)


@router.put("/{house_id}/devices/{device_id}")
async def update_device(house_id: int, device_id: int, body: DeviceUpdate,
                        user: UserModel = Depends(require_house_access), session: AsyncSession = Depends(get_session)):
    device = await devices.get_device(session, house_id, device_id)
    await devices.update_device(session, device, body, sim.sim_datetime, _actor(user))
    return device_dict(device)


@router.post("/{house_id}/devices/{device_id}/toggle")
async def toggle_device(house_id: int, device_id: int, user: UserModel = Depends(require_house_access),
                        session: AsyncSession = Depends(get_session)):
    device = await devices.get_device(session, house_id, device_id)
    await devices.toggle_device(session, device, sim.sim_datetime, _actor(user))
    return device_dict(device)


@router.delete("/{house_id}/devices/{device_id}")
async def delete_device(house_id: int, device_id: int, _: UserModel = Depends(require_house_access),
                        session: AsyncSession = Depends(get_session)):
    device = await devices.get_device(session, house_id, device_id)
    name = device.name
    await devices.delete_device(session, device)
    return {"device_id": device_id, "name": name, "message": "Dispozitiv sters"}
