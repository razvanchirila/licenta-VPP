"""
The live loop's load comes from the devices seeded from dispozitive.csv, its PV from the 2023 data and its
prices from SIM_PRICE_YEAR (SIM_DATA=real). Same temporary-database setup as test_api.py; steps are triggered by hand.
"""
import asyncio
import logging
import os
import tempfile
from datetime import date

import numpy as np
import pytest

_TMP = tempfile.mkdtemp(prefix="vpp-test-")
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/"),
    "JWT_SECRET_KEY": "test-secret-key-not-for-production",
    "SIM_AUTOSTART": "false",
    "SIM_START_DATE": "2025-06-01",
    "SIM_CONTROLLER": "reguli",
})

from fastapi.testclient import TestClient  # noqa: E402

from app.db.database import close_db, get_session_context, init_db  # noqa: E402
from app.db.init_data import seed_houses  # noqa: E402
from app.services import simulation_loop  # noqa: E402
from app.services.simulation_loop import data_day, sim  # noqa: E402
from app.services.users import create_user  # noqa: E402
from main import app  # noqa: E402
from vpp_core import data_sources as ds  # noqa: E402
from vpp_core import load_model as lm  # noqa: E402
from vpp_core.scenario_real import NETWORK_ADDER, SUPPLY_MARGIN, VAT  # noqa: E402

PASSWORD = "parola123"
DAY = date(2025, 6, 1)
DT_H = 0.25


async def _seed():
    await init_db()
    async with get_session_context() as session:
        await seed_houses(session)
        await create_user(session, "admin", PASSWORD, None, True)
        await create_user(session, "user1", PASSWORD, 1, False)
    await close_db()


@pytest.fixture(scope="module")
def client():
    asyncio.run(_seed())
    with TestClient(app) as c:
        yield c


def _login(client, username):
    r = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def admin(client):
    headers = _login(client, "admin")
    assert client.post("/api/config/reset", headers=headers).status_code == 200
    assert client.post("/api/sim/reset", headers=headers).status_code == 200
    return headers


def _step_house(client, admin, house_id: int, t: int) -> dict:
    """One step at (DAY, t) of the loop, which is not running; returns the house row of the result."""
    sim.day, sim.t = DAY, t
    r = client.post("/api/sim/step", headers=admin)
    assert r.status_code == 200, r.text
    return next(h for h in r.json()["houses"] if h["id"] == house_id)


def _expected_profiles(house_id: int, day: date = DAY, seed: int = 42) -> dict[str, np.ndarray]:
    """name -> kW profile of the day, drawn exactly as the loop (and community_load) draw them."""
    rng = lm.house_rng(seed + day.toordinal(), house_id)
    return {app.dispozitiv: lm.appliance_profile(app, day, 1, DT_H, rng)
            for app in lm.by_house(lm.load_appliances())[house_id]}


# ---------------------------------------------------------------- devices

def test_seeded_devices_match_the_csv(client, admin):
    groups = lm.by_house(lm.load_appliances())
    for house in client.get("/api/houses", headers=admin).json():
        seeded = [d for d in house["devices"] if d["schedule"] is not None]
        apps = groups[house["id"]]
        assert [d["name"] for d in seeded] == [a.dispozitiv for a in apps]
        assert [d["critical"] for d in seeded] == [not a.flexibil for a in apps]
        assert [d["power_w"] for d in seeded] == [a.putere_w for a in apps]
        assert all(d["status_on"] for d in seeded)
        assert [d["schedule"]["mode"] for d in seeded] == [a.mod for a in apps]
    ev = next(d for d in client.get("/api/houses/4/devices", headers=admin).json() if "mașină electrică" in d["name"])
    assert ev["schedule"]["interval"] == "22-6" and ev["schedule"]["cycles_per_week"] == 3


def test_house_load_is_the_sum_of_its_switched_on_devices(client, admin):
    profiles = _expected_profiles(1)
    total = sum(profiles.values())
    boiler = profiles["boiler electric"]
    t = int(np.argmax(boiler > 0.5))                       # a step where the boiler is running
    assert boiler[t] > 0.5
    devices = client.get("/api/houses/1/devices", headers=admin).json()
    boiler_id = next(d["id"] for d in devices if d["name"] == "boiler electric")

    row = _step_house(client, admin, 1, t)
    assert row["load_kw"] == pytest.approx(total[t], abs=1e-3)
    assert row["device_kw"] == row["load_kw"]
    house = client.get("/api/houses/1", headers=admin).json()
    assert house["L_crit_kw"] + house["L_noncrit_kw"] == pytest.approx(total[t], abs=2e-3)
    dev = next(d for d in house["devices"] if d["id"] == boiler_id)
    assert dev["current_power_kw"] == pytest.approx(boiler[t], abs=1e-4)
    assert dev["accumulated_energy_kwh"] == pytest.approx(boiler[t] * DT_H, abs=1e-4)

    r = client.post(f"/api/houses/1/devices/{boiler_id}/toggle", headers=admin)
    assert r.status_code == 200 and r.json()["status_on"] is False and r.json()["current_power_kw"] == 0.0
    row = _step_house(client, admin, 1, t)
    assert row["load_kw"] == pytest.approx(total[t] - boiler[t], abs=1e-3)

    client.post(f"/api/houses/1/devices/{boiler_id}/toggle", headers=admin)
    row = _step_house(client, admin, 1, t)
    assert row["load_kw"] == pytest.approx(total[t], abs=1e-3)


def test_seeded_load_equals_the_scenario_generator(client, admin):
    """With every seeded device on, the loop draws what community_load() draws for that day."""
    seed = 42 + DAY.toordinal()
    crit, flex = lm.community_load(sim.community, lm.DISPOZITIVE_CSV, DAY, 1, DT_H, seed)
    for t in (0, 30, 76):
        row = _step_house(client, admin, 2, t)
        assert row["load_kw"] == pytest.approx(crit[1, t] + flex[1, t], abs=1e-3)


def test_manual_device_adds_a_constant_load(client, admin):
    total = sum(_expected_profiles(1).values())
    r = client.post("/api/houses/1/devices", json={"name": "Radiator", "power_w": 500, "status_on": True},
                    headers=admin)
    assert r.status_code == 201 and r.json()["schedule"] is None
    device_id = r.json()["id"]
    row = _step_house(client, admin, 1, 10)
    assert row["load_kw"] == pytest.approx(total[10] + 0.5, abs=1e-3)
    dev = next(d for d in client.get("/api/houses/1/devices", headers=admin).json() if d["id"] == device_id)
    assert dev["current_power_kw"] == 0.5 and dev["accumulated_energy_kwh"] == pytest.approx(0.5 * DT_H)
    assert client.delete(f"/api/houses/1/devices/{device_id}", headers=admin).status_code == 200
    row = _step_house(client, admin, 1, 10)
    assert row["load_kw"] == pytest.approx(total[10], abs=1e-3)


def test_critical_seeded_device_cannot_be_switched_off(client, admin):
    fridge = next(d for d in client.get("/api/houses/1/devices", headers=admin).json() if d["name"] == "frigider")
    assert fridge["critical"] is True
    assert client.post(f"/api/houses/1/devices/{fridge['id']}/toggle", headers=admin).status_code == 400


# ---------------------------------------------------------------- real data

def test_data_day_mapping():
    assert data_day(date(2025, 6, 1), 2023) == date(2023, 6, 1)
    assert data_day(date(2024, 2, 29), 2023) == date(2023, 2, 28)
    assert data_day(date(2026, 1, 1), 2023) == date(2023, 1, 1)


def test_real_mode_prices_are_the_pzu_of_the_price_year_with_the_tariff(client, admin):
    year = sim.data_year
    assert year in ds.PRICE_YEARS
    status = client.get("/api/sim/status", headers=admin).json()
    assert status["data_source"] == "real" and status["data_year"] == year
    config = client.get("/api/config", headers=admin).json()
    assert config["data_source"] == "real" and config["data_year"] == year

    pzu = ds.load_prices_lei_kwh(year)[date(2023, 6, 1).timetuple().tm_yday - 1]      # 1 June of the price year
    prices = client.get("/api/sim/prices", headers=admin).json()["prices"]
    for t in (0, 13, 50, 95):
        expected = (pzu[int(t * DT_H)] + SUPPLY_MARGIN + NETWORK_ADDER) * (1 + VAT)
        assert prices[t]["price_import"] == pytest.approx(expected, abs=1e-4), t
        assert prices[t]["price_export"] == pytest.approx(pzu[int(t * DT_H)] + SUPPLY_MARGIN, abs=1e-4), t
    sim.day, sim.t = DAY, 50
    step = client.post("/api/sim/step", headers=admin).json()
    assert step["data_source"] == "real"
    assert step["price"]["import"] == pytest.approx((pzu[12] + SUPPLY_MARGIN + NETWORK_ADDER) * (1 + VAT), abs=1e-4)
    pv = ds.load_pv_kw_per_kwp()[date(2023, 6, 1).timetuple().tm_yday - 1]     # kW/kWp, 100 kWp in total
    assert 0.85 * pv[11:14].min() <= step["community"]["pv_kw"] / 100 <= 1.15 * pv[11:14].max()


def test_synthetic_fallback_when_the_csvs_are_missing(client, admin, monkeypatch, caplog, tmp_path):
    pzu0 = ds.load_prices_lei_kwh(sim.data_year)[date(2023, 6, 1).timetuple().tm_yday - 1][0]
    monkeypatch.setattr(ds, "DATA_DIR", tmp_path)
    sim.scenario = None
    with caplog.at_level(logging.WARNING, logger=simulation_loop.__name__):
        sim.day, sim.t = DAY, 0
        step = client.post("/api/sim/step", headers=admin).json()
    assert step["data_source"] == "sintetic"
    assert client.get("/api/sim/status", headers=admin).json()["data_source"] == "sintetic"
    assert any("Date reale indisponibile" in rec.message and f"prices_ro_{sim.data_year}.csv" in rec.message
               for rec in caplog.records)
    assert step["price"]["import"] != pytest.approx((pzu0 + SUPPLY_MARGIN + NETWORK_ADDER) * (1 + VAT), abs=1e-4)

    monkeypatch.undo()
    sim.scenario = None
    sim.day, sim.t = DAY, 0
    assert client.post("/api/sim/step", headers=admin).json()["data_source"] == "real"
