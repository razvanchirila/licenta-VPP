from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.settings import settings
from vpp_core.load_model import (
    CASE_CSV,
    DISPOZITIVE_CSV,
    Appliance,
    House,
    compose_houses,
    load_catalog,
    programs_to_json,
)
from vpp_core.params import CommunityParams, default_community

from .models import (
    BatteryModel,
    DeviceModel,
    HouseModel,
    TradingPreferencesModel,
    VPPReserveModel,
    WalletModel,
    WalletTransactionModel,
)

logger = logging.getLogger(__name__)


def _initial_tx(wallet: WalletModel, amount: float, sim_ts: datetime) -> WalletTransactionModel:
    return WalletTransactionModel(
        wallet=wallet, transaction_type="initial", amount_lei=amount, description="Sold initial",
        balance_after=amount, sim_timestamp=sim_ts,
    )


def device_from_appliance(house: HouseModel, app: Appliance) -> DeviceModel:
    return DeviceModel(
        house=house, name=app.dispozitiv, power_w=app.putere_w, critical=not app.flexibil, status_on=True,
        mode=app.tip, program=programs_to_json(app.programe),
    )


def _composition_by_house(community: CommunityParams) -> dict[int, House]:
    """The composition the simulator generates for each house id."""
    missing = [path for path in (DISPOZITIVE_CSV, CASE_CSV) if not path.exists()]
    if missing:
        logger.warning("%s lipseste: casele pornesc fara dispozitive", ", ".join(map(str, missing)))
        return {}
    houses = compose_houses((hp.id for hp in community.houses), load_catalog())
    return {house.casa: house for house in houses}


async def seed_houses(session: AsyncSession, community: CommunityParams | None = None) -> list[HouseModel]:
    """Idempotent: nothing happens when houses already exist."""
    existing = (await session.execute(select(HouseModel))).scalars().all()
    if existing:
        return list(existing)

    community = community or default_community()
    compositions = _composition_by_house(community)
    sim_ts = datetime.combine(settings.sim_start_date, datetime.min.time())
    houses, n_devices = [], 0
    for hp in community.houses:
        house = HouseModel(id=hp.id, name=f"Casa {hp.id}", mode=hp.mode, has_pv=hp.pv_kwp > 0, pv_capacity_kw=hp.pv_kwp)
        composition = compositions.get(hp.id)
        if composition:
            house.description, house.people = composition.descriere, composition.persoane
            house.home_daytime, house.heating = composition.acasa_ziua, composition.incalzire
            house.insulation = composition.izolatie
        session.add(house)
        for app in composition.appliances if composition else ():
            session.add(device_from_appliance(house, app))
            n_devices += 1
        if hp.battery:
            b = hp.battery
            session.add(BatteryModel(
                house=house, capacity_kwh=b.capacity_kwh, soc_kwh=hp.initial_soc_kwh, soc_min_kwh=b.soc_min_kwh,
                p_ch_max_kw=b.p_ch_max_kw, p_dis_max_kw=b.p_dis_max_kw, eta_ch=b.eta_ch, eta_dis=b.eta_dis,
            ))
        session.add(TradingPreferencesModel(house=house, selling_enabled=hp.p2p_enabled, buying_enabled=hp.p2p_enabled))
        wallet = WalletModel(house=house, balance_lei=settings.initial_wallet_lei, transaction_count=1)
        session.add(wallet)
        session.add(_initial_tx(wallet, settings.initial_wallet_lei, sim_ts))
        session.add(VPPReserveModel(house=house))
        houses.append(house)

    operator = (await session.execute(select(WalletModel).where(WalletModel.house_id.is_(None)))).scalar_one_or_none()
    if operator is None:
        operator = WalletModel(house_id=None, balance_lei=settings.operator_wallet_lei, transaction_count=1)
        session.add(operator)
        session.add(_initial_tx(operator, settings.operator_wallet_lei, sim_ts))

    await session.flush()
    # explicit ids do not advance the serial sequence; without this the next insert would reuse id 1
    await session.execute(text("SELECT setval(pg_get_serial_sequence('houses', 'id'), (SELECT max(id) FROM houses))"))
    logger.info("Seeded %d houses, %d devices", len(houses), n_devices)
    return houses
