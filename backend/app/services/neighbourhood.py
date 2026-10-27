"""
The neighbourhood as the app sees it: each house's people, daytime presence, heating, insulation and optional
devices, kept on the house rows. Editing a house recomposes its seeded devices from the catalog, the way
load_model composes a row of case.csv; devices added by hand stay. backend/data/case.csv stays the reference:
reset_all puts it back and export writes the current state in its format.
"""
from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.init_data import device_from_appliance
from app.db.models import HouseModel
from vpp_core import thermal
from vpp_core.load_model import (
    FARA_INCALZIRE,
    TIPURI,
    Catalog,
    HouseSpec,
    check_spec,
    compose_spec,
    house_spec,
    load_catalog,
    specs_to_csv,
)


def catalog_view(catalog: Catalog) -> dict:
    return {"optional": catalog.names("ales"), "heating": [FARA_INCALZIRE, *catalog.names("incalzire")],
            "insulation": list(thermal.IZOLATII), "always": catalog.names("toti")}


def spec_of(house: HouseModel, catalog: Catalog) -> HouseSpec:
    optional = set(catalog.names("ales"))
    names = [d.name for d in house.devices if d.mode and d.name in optional]
    return HouseSpec(house.id, house.description, house.people, house.home_daytime, house.heating,
                     house.insulation, tuple(dict.fromkeys(names)))


def spec_dict(spec: HouseSpec) -> dict:
    return {"id": spec.casa, "description": spec.descriere, "people": spec.persoane,
            "home_daytime": spec.acasa_ziua, "heating": spec.incalzire, "insulation": spec.izolatie,
            "devices": list(spec.dispozitive)}


async def apply_spec(session: AsyncSession, house: HouseModel, spec: HouseSpec, catalog: Catalog) -> None:
    """Raises ValueError when the spec does not fit the catalog; the house needs its devices loaded."""
    check_spec(spec, catalog.names("ales"), catalog.names("incalzire"))
    for device in [d for d in house.devices if d.mode]:
        house.devices.remove(device)
        await session.delete(device)
    house.description, house.people, house.home_daytime = spec.descriere, spec.persoane, spec.acasa_ziua
    house.heating, house.insulation = spec.incalzire, spec.izolatie
    for app in compose_spec(house.id, spec, catalog).appliances:
        session.add(device_from_appliance(house, app))
    await session.flush()


async def reset_all(session: AsyncSession, houses: list[HouseModel]) -> None:
    catalog = load_catalog()
    for house in houses:
        await apply_spec(session, house, house_spec(house.id, catalog), catalog)


def export_csv(houses: list[HouseModel]) -> str:
    catalog = load_catalog()
    return specs_to_csv(spec_of(h, catalog) for h in sorted(houses, key=lambda h: h.id))


async def upgrade_old_devices(session: AsyncSession, houses: list[HouseModel]) -> int:
    """Houses seeded with the old catalog (modes continuu / zilnic / ciclic, no program) get their composition
    from case.csv again; returns how many. The per-device energy logs are emptied first: deleting millions of
    them row by row outlasts the health check, and the old devices they belong to are gone anyway."""
    old = [h for h in houses if any(d.mode and (d.mode not in TIPURI or d.program == "[]") for d in h.devices)]
    if old:
        await session.execute(text("TRUNCATE energy_logs"))
        await reset_all(session, old)
        logging.getLogger(__name__).info("Casele %s au primit dispozitivele din case.csv", [h.id for h in old])
    return len(old)
