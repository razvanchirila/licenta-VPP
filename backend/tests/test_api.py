"""
Tests of the HTTP API on the PostgreSQL test database (TEST_DATABASE_URL, see conftest.py).
The simulation loop is loaded but not started; steps are triggered by hand.
"""
import asyncio
import os
from dataclasses import replace
from datetime import datetime, timedelta

import numpy as np
import pytest
from conftest import api_database_url, recreate_tables

os.environ.update({
    "DATABASE_URL": api_database_url(),
    "JWT_SECRET_KEY": "test-secret-key-not-for-production",
    "SIM_AUTOSTART": "false",
    "SIM_START_DATE": "2025-06-01",
    "SIM_CONTROLLER": "reguli",
    "INITIAL_WALLET_LEI": "100",
})

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from app.db.database import close_db, get_engine, get_session_context  # noqa: E402
from app.db.init_data import seed_houses  # noqa: E402
from app.db.repositories import UserRepository  # noqa: E402
from app.services import settlement  # noqa: E402
from app.services.auth import create_access_token  # noqa: E402
from app.services.rate_limit import login_failures, registrations  # noqa: E402
from app.services.simulation_loop import sim  # noqa: E402
from app.services.users import create_user  # noqa: E402
from app.settings import settings  # noqa: E402
from main import app  # noqa: E402

PASSWORD = "parola123"


async def _seed():
    await recreate_tables()
    async with get_session_context() as session:
        await seed_houses(session)
        await create_user(session, "admin", PASSWORD, None, True)
        await create_user(session, "user1", PASSWORD, 1, False)
        await create_user(session, "user2", PASSWORD, 2, False)
        await create_user(session, "user3", PASSWORD, 3, False)     # houses 1-8 have a battery, 9-10 do not
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
    return _login(client, "admin")


@pytest.fixture(scope="module")
def user1(client):
    return _login(client, "user1")


@pytest.fixture(scope="module")
def user3(client):
    return _login(client, "user3")


def test_health_is_public(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["simulation"]["n_houses"] == 10


def test_root_redirects_to_docs(client):
    """The API no longer serves a dashboard; the operator panel lives in the web container."""
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"
    assert client.get("/static/app.js").status_code == 404


def test_login_rejects_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "user1", "password": "gresit"})
    assert r.status_code == 401


def test_login_locks_a_username_after_repeated_failures(client):
    for _ in range(settings.login_max_failures):
        r = client.post("/api/auth/login", json={"username": "user2", "password": "gresit"})
        assert r.status_code == 401
    r = client.post("/api/auth/login", json={"username": "user2", "password": PASSWORD})
    assert r.status_code == 429 and "Retry-After" in r.headers
    assert client.post("/api/auth/login", json={"username": "user1", "password": PASSWORD}).status_code == 200
    login_failures.reset()
    assert client.post("/api/auth/login", json={"username": "user2", "password": PASSWORD}).status_code == 200


def test_register_is_rate_limited(client, monkeypatch):
    registrations.reset()
    monkeypatch.setattr(settings, "register_max_per_hour", 2)
    for i in range(2):
        r = client.post("/api/auth/register", json={"username": f"limita{i}", "password": PASSWORD})
        assert r.status_code == 201
    r = client.post("/api/auth/register", json={"username": "limita2", "password": PASSWORD})
    assert r.status_code == 429
    registrations.reset()


def test_login_returns_house_and_role(client):
    r = client.post("/api/auth/login", json={"username": "user1", "password": PASSWORD})
    body = r.json()
    assert body["house_id"] == 1 and body["is_admin"] is False and body["token_type"] == "bearer"


def test_protected_routes_need_a_token(client):
    assert client.get("/api/me/house").status_code == 401
    assert client.get("/api/vpp/state").status_code == 401
    assert client.get("/api/sim/status", headers={"Authorization": "Bearer nu.e.token"}).status_code == 401


def test_admin_only_routes(client, user1, admin):
    assert client.post("/api/sim/step", headers=user1).status_code == 403
    assert client.get("/api/houses", headers=user1).status_code == 403
    assert client.put("/api/config", json={"tick_seconds": 5}, headers=user1).status_code == 403
    assert client.get("/api/houses", headers=admin).status_code == 200


def test_user_sees_only_own_house(client, user1, admin):
    assert client.get("/api/houses/1", headers=user1).status_code == 200
    assert client.get("/api/houses/2", headers=user1).status_code == 403
    assert client.get("/api/wallet/2", headers=user1).status_code == 403
    assert client.get("/api/trading/preferences/2", headers=user1).status_code == 403
    assert client.get("/api/houses/2", headers=admin).status_code == 200


def test_nan_and_out_of_range_inputs_are_rejected(client, user1):
    r = client.post("/api/me/devices", content='{"name": "x", "power_w": NaN}',
                    headers={**user1, "Content-Type": "application/json"})
    assert r.status_code == 422
    r = client.post("/api/wallet/1/transfer-to-vpp", json={"energy_kwh": -1}, headers=user1)
    assert r.status_code == 422


def test_step_logs_energy_and_updates_soc(client, user3, admin):
    r = client.post("/api/me/devices", json={"name": "Frigider", "power_w": 200, "critical": True, "status_on": True},
                    headers=user3)
    assert r.status_code == 201, r.text
    device_id = r.json()["id"]
    soc_before = client.get("/api/houses/3/battery", headers=user3).json()["soc_kwh"]

    r = client.post("/api/sim/step", headers=admin)
    assert r.status_code == 200, r.text
    step = r.json()
    assert len(step["houses"]) == 10 and step["controller"] == "reguli"
    house3 = next(h for h in step["houses"] if h["id"] == 3)
    assert house3["device_kw"] == house3["load_kw"] > 0.2      # the fridge plus the seeded appliances
    # node balance of house 3: sources == sinks
    sources = house3["pv_kw"] - house3["curtail_kw"] + house3["dis_kw"] + house3["imp_kw"] + house3["p2p_in_kw"]
    sinks = house3["load_kw"] - house3["shed_kw"] + house3["ch_kw"] + house3["exp_kw"] + house3["p2p_out_kw"]
    assert sources == pytest.approx(sinks, abs=2e-3)

    devices = client.get("/api/me/devices", headers=user3).json()
    dev = next(d for d in devices if d["id"] == device_id)
    dt_h = sim.dt_h
    assert dev["accumulated_energy_kwh"] == pytest.approx(0.2 * dt_h, abs=1e-4)   # 200 W for one step
    assert dev["current_power_kw"] == pytest.approx(0.2) and dev["schedule"] is None
    today = client.get("/api/me/energy/today", headers=user3).json()
    assert today["steps"] == 1 and today["device_kwh"] == pytest.approx(house3["load_kw"] * dt_h, abs=1e-3)
    stats = client.get("/api/stats/summary?period=day", headers=user3).json()
    assert stats["total_kwh"] == pytest.approx(house3["load_kw"] * dt_h, abs=1e-3)   # energy_logs add up to the load
    soc_after = client.get("/api/houses/3/battery", headers=user3).json()["soc_kwh"]
    assert soc_after == pytest.approx(house3["soc_kwh"], abs=1e-3)
    assert soc_after != soc_before or house3["ch_kw"] == 0 == house3["dis_kw"]
    status = client.get("/api/sim/status", headers=user3).json()
    assert status["total_steps"] == 1 and status["sim_time"] == f"00:{settings.sim_step_minutes:02d}"


def test_manual_trade_is_settled_atomically(client, admin):
    w1 = client.get("/api/wallet/1", headers=admin).json()["balance_lei"]
    w2 = client.get("/api/wallet/2", headers=admin).json()["balance_lei"]
    r = client.post("/api/admin/trades", json={"seller_house_id": 1, "buyer_house_id": 2, "energy_kwh": 4,
                                               "price_lei_kwh": 0.5}, headers=admin)
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "settled" and r.json()["total_value_lei"] == 2.0
    assert client.get("/api/wallet/1", headers=admin).json()["balance_lei"] == pytest.approx(w1 + 2)
    assert client.get("/api/wallet/2", headers=admin).json()["balance_lei"] == pytest.approx(w2 - 2)
    tx = client.get("/api/wallet/2/transactions?transaction_type=debit", headers=admin).json()["transactions"]
    assert tx[0]["reference_id"] == r.json()["id"] and tx[0]["amount_lei"] == 2.0


def test_trade_with_insufficient_funds_is_rejected(client, admin):
    w1 = client.get("/api/wallet/1", headers=admin).json()["balance_lei"]
    w2 = client.get("/api/wallet/2", headers=admin).json()["balance_lei"]
    r = client.post("/api/admin/trades", json={"seller_house_id": 1, "buyer_house_id": 2, "energy_kwh": 1000,
                                               "price_lei_kwh": 1.0}, headers=admin)
    assert r.status_code == 201
    assert r.json()["status"] == "rejected" and "insuficiente" in r.json()["reason"]
    assert client.get("/api/wallet/1", headers=admin).json()["balance_lei"] == pytest.approx(w1)
    assert client.get("/api/wallet/2", headers=admin).json()["balance_lei"] == pytest.approx(w2)
    hist = client.get("/api/trading/history/2?status=rejected", headers=admin).json()
    assert hist["count"] >= 1 and hist["transactions"][0]["transaction_type"] == "buy"


def test_failed_settlement_rolls_back_the_buyer_debit(client, admin, monkeypatch):
    """The buyer is debited first; if the seller credit then fails nothing must be committed."""
    w1 = client.get("/api/wallet/1", headers=admin).json()["balance_lei"]
    w2 = client.get("/api/wallet/2", headers=admin).json()["balance_lei"]
    original = settlement.SettlementService._move
    calls = {"n": 0}

    def flaky(self, wallet, amount, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated failure on the seller credit")
        return original(self, wallet, amount, *args, **kwargs)

    monkeypatch.setattr(settlement.SettlementService, "_move", flaky)
    with pytest.raises(RuntimeError):
        client.post("/api/admin/trades", json={"seller_house_id": 1, "buyer_house_id": 2, "energy_kwh": 1,
                                               "price_lei_kwh": 1.0}, headers=admin)
    monkeypatch.undo()
    assert calls["n"] == 2
    assert client.get("/api/wallet/1", headers=admin).json()["balance_lei"] == pytest.approx(w1)
    assert client.get("/api/wallet/2", headers=admin).json()["balance_lei"] == pytest.approx(w2)


def test_settled_trade_has_one_debit_and_one_credit_of_equal_value(client, admin):
    """Settlement invariants: debit == credit == energy x price, both referencing the trade, exactly once."""
    r = client.post("/api/admin/trades", json={"seller_house_id": 3, "buyer_house_id": 4, "energy_kwh": 1.5,
                                               "price_lei_kwh": 0.8}, headers=admin)
    assert r.status_code == 201 and r.json()["status"] == "settled"
    trade_id, value = r.json()["id"], r.json()["total_value_lei"]
    debits = [t for t in client.get("/api/wallet/4/transactions", headers=admin).json()["transactions"]
              if t["reference_id"] == trade_id]
    credits = [t for t in client.get("/api/wallet/3/transactions", headers=admin).json()["transactions"]
               if t["reference_id"] == trade_id]
    assert len(debits) == 1 and len(credits) == 1
    assert debits[0]["transaction_type"] == "debit" and credits[0]["transaction_type"] == "credit"
    assert debits[0]["amount_lei"] == credits[0]["amount_lei"] == pytest.approx(value) == pytest.approx(1.2)
    r = client.post("/api/admin/trades", json={"seller_house_id": 3, "buyer_house_id": 3, "energy_kwh": 1,
                                               "price_lei_kwh": 0.5}, headers=admin)
    assert r.status_code == 400 and "diferite" in r.json()["detail"]


def test_transfer_to_vpp_moves_energy_and_money(client, user3, admin):
    soc = client.get("/api/houses/3/battery", headers=user3).json()["soc_kwh"]
    balance = client.get("/api/wallet/3", headers=user3).json()["balance_lei"]
    operator = client.get("/api/wallet/operator", headers=admin).json()["balance_lei"]
    r = client.post("/api/wallet/3/transfer-to-vpp", json={"energy_kwh": 2}, headers=user3)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payment_lei"] == pytest.approx(1.0)           # base rate 0.5 lei/kWh
    assert body["new_battery_soc_kwh"] == pytest.approx(soc - 2, abs=1e-3)
    assert body["vpp_reserve"]["reserved_kwh"] == pytest.approx(2)
    assert client.get("/api/wallet/3", headers=user3).json()["balance_lei"] == pytest.approx(balance + 1)
    assert client.get("/api/wallet/operator", headers=admin).json()["balance_lei"] == pytest.approx(operator - 1)
    assert client.get("/api/houses/3/battery", headers=user3).json()["soc_kwh"] == pytest.approx(soc - 2, abs=1e-3)
    r = client.post("/api/wallet/3/transfer-to-vpp", json={"energy_kwh": 500}, headers=user3)
    assert r.status_code == 400


def test_money_is_conserved_across_wallets(client, admin):
    """P2P moves money between houses and VPP payments come from the operator: the sum never changes."""
    houses = client.get("/api/houses", headers=admin).json()
    operator = client.get("/api/wallet/operator", headers=admin).json()["balance_lei"]
    total = sum(h["wallet_balance_lei"] for h in houses) + operator
    assert total == pytest.approx(10 * 100 + 10000, abs=0.05)


def test_concurrent_settlements_do_not_lose_money(client):
    """Each trade runs in its own session at the same time; without row locks a stale balance read by one
    session overwrote what another had just committed and the community lost money."""
    async def run():
        engine = create_async_engine(settings.database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        async def balances():
            async with engine.connect() as conn:
                rows = await conn.execute(text("SELECT house_id, balance_lei FROM wallets"))
                return {h: b for h, b in rows}

        async def trade(seller, buyer):
            async with factory() as session:
                await settlement.SettlementService(session).settle_trade(
                    settlement.Trade(seller, buyer, 0.5, 1.0, 1.0), datetime(2025, 6, 1, 12))
                await asyncio.sleep(0)
                await session.commit()

        try:
            before = await balances()
            pairs = [(5, 6), (6, 5), (7, 5), (5, 7), (6, 7)] * 6
            await asyncio.gather(*(trade(s, b) for s, b in pairs))
            after = await balances()
        finally:
            await engine.dispose()
        return before, after, pairs

    before, after, pairs = asyncio.run(run())
    assert sum(after.values()) == pytest.approx(sum(before.values()), abs=1e-6)
    for house in (5, 6, 7):
        net = sum(0.5 for s, _ in pairs if s == house) - sum(0.5 for _, b in pairs if b == house)
        assert after[house] == pytest.approx(before[house] + net, abs=1e-6)


def test_settings_change_reaches_the_simulation(client, user3, admin):
    r = client.put("/api/me/settings", json={"mode": "Profit", "backup_reserve_percent": 30}, headers=user3)
    assert r.status_code == 200 and r.json()["mode"] == "Profit" and r.json()["backup_reserve_percent"] == 30
    step = client.post("/api/sim/step", headers=admin).json()
    house3 = next(h for h in step["houses"] if h["id"] == 3)
    assert house3["mode"] == "Profit"
    assert house3["soc_kwh"] >= 0.3 * 16 - 1e-6          # one SE-F16 module


def test_reserve_above_soc_does_not_create_energy(client, user1, admin):
    """Raising the backup reserve above the stored energy used to clamp the SOC up to the reserve."""
    battery = client.get("/api/houses/1/battery", headers=user1).json()
    excess = round(battery["soc_kwh"] - 0.2 * battery["capacity_kwh"], 2)
    if excess > 0:
        r = client.post("/api/wallet/1/transfer-to-vpp", json={"energy_kwh": excess}, headers=user1)
        assert r.status_code == 200
    soc = client.get("/api/houses/1/battery", headers=user1).json()["soc_kwh"]
    assert client.put("/api/me/settings", json={"backup_reserve_percent": 60}, headers=user1).status_code == 200
    try:
        for _ in range(2):
            step = client.post("/api/sim/step", headers=admin).json()
            house = next(h for h in step["houses"] if h["id"] == 1)
            expected = soc + (0.95 * house["ch_kw"] - house["dis_kw"] / 0.95) * step["dt_h"]
            assert house["soc_kwh"] == pytest.approx(expected, abs=2e-3)
            assert house["dis_kw"] == 0
            soc = house["soc_kwh"]
    finally:
        client.put("/api/me/settings", json={"backup_reserve_percent": 10}, headers=user1)


def test_speed_message_is_written_the_romanian_way(client, admin):
    for seconds, message in ((0.5, "Un pas la 0,5 s"), (2, "Un pas la 2 s")):
        assert client.post("/api/sim/speed", json={"tick_seconds": seconds}, headers=admin).json()["message"] == message


def test_config_switches_controller_to_mpc(client, admin, user1):
    r = client.put("/api/config", json={"controller": "mpc"}, headers=admin)
    assert r.status_code == 200 and r.json()["config"]["controller"] == "mpc"
    step = client.post("/api/sim/step", headers=admin).json()
    assert step["controller"] == "mpc"
    assert client.get("/api/config", headers=user1).json()["controller"] == "mpc"
    assert client.post("/api/config/reset", headers=admin).json()["config"]["controller"] == "reguli"


def test_prices_and_history(client, user1, admin):
    prices = client.get("/api/sim/prices", headers=user1).json()
    assert len(prices["prices"]) == round(24 / sim.dt_h)
    assert prices["prices"][0]["price_import"] > prices["prices"][0]["price_p2p"]
    history = client.get("/api/sim/history?limit=2", headers=admin).json()
    assert history["count"] == 2 and "community" in history["steps"][-1]
    assert client.get("/api/sim/history", headers=user1).status_code == 403     # the steps hold every house


def test_vpp_state_and_stats_aggregates(client, user1):
    state = client.get("/api/vpp/state", headers=user1).json()
    assert state["total_houses"] == 10 and state["houses_with_battery"] + state["houses_without_battery"] == 10
    assert state["total_battery_capacity_kwh"] > 0 and 0 <= state["avg_battery_soc_percent"] <= 100
    assert state["total_L_crit_kw"] >= 0.2          # the 200 W fridge of house 3 is on
    assert state["last_step"] is not None and "houses" not in state["last_step"]
    stats = client.get("/api/vpp/stats", headers=user1).json()
    assert stats["today"]["date"] == "2025-06-01" and stats["today"]["load_kwh"] > 0
    top = client.get("/api/stats/top-consumers?period=day", headers=user1).json()
    summary = client.get("/api/stats/summary?period=day", headers=user1).json()
    assert top["total_house_kwh"] == pytest.approx(summary["total_kwh"])


def test_energy_history_days_without_data_have_the_full_shape(client, user1):
    rows = client.get("/api/me/energy/history?days=3", headers=user1).json()
    assert len(rows) == 3 and rows[-1]["date"] == "2025-06-01" and rows[-1]["has_data"] is True
    keys = set(rows[-1])
    for row in rows:
        assert set(row) == keys                      # same EnergyTotals keys whether or not has_data
    assert rows[0]["has_data"] is False and rows[0]["savings_lei"] == 0.0


def test_chart_periods_and_bad_date(client, user1):
    for period, minutes in (("day", settings.sim_step_minutes), ("week", 180), ("month", 1440)):
        r = client.get(f"/api/me/energy/chart?period={period}", headers=user1)
        assert r.status_code == 200 and r.json()["interval_minutes"] == minutes, period
    assert client.get("/api/me/energy/chart?date=2025-13-40", headers=user1).status_code == 400
    impact = client.get("/api/me/energy/impact", headers=user1).json()
    assert impact["monthly_savings"][-1]["current"] is True and len(impact["monthly_savings"]) == 6


def test_stats_chart_groups_by_hour_day_and_week(client, user3):
    """The same energy_logs grouped by hour, day and ISO week: the date grouping must work on every database."""
    def chart(start):
        r = client.get(f"/api/stats/chart?start_date={start}&end_date=2025-06-01", headers=user3)
        assert r.status_code == 200, r.text
        return r.json()

    hourly, daily, weekly = chart("2025-06-01"), chart("2025-05-20"), chart("2025-04-01")
    assert (hourly["granularity"], daily["granularity"], weekly["granularity"]) == ("hourly", "daily", "weekly")
    assert hourly["data_points"][0]["timestamp"] == "2025-06-01T00:00:00"
    assert [p["timestamp"] for p in daily["data_points"]] == ["2025-06-01T00:00:00"]
    assert [p["timestamp"] for p in weekly["data_points"]] == ["2025-05-26T00:00:00"]     # Monday of that week
    total = sum(p["value_kwh"] for p in hourly["data_points"])
    assert total > 0
    assert daily["data_points"][0]["value_kwh"] == pytest.approx(total)
    assert weekly["data_points"][0]["value_kwh"] == pytest.approx(total)
    impact = client.get("/api/me/energy/impact", headers=user3).json()
    assert impact["monthly_savings"][-1]["has_data"] is True and impact["monthly_savings"][0]["has_data"] is False


def test_stats_chart_range_is_limited(client, user3):
    def chart(start):
        return client.get(f"/api/stats/chart?start_date={start}&end_date=2025-06-01", headers=user3)

    assert chart("2024-06-01").status_code == 200            # the "An" view of the app
    r = chart("2024-04-01")
    assert r.status_code == 400 and "400 de zile" in r.json()["detail"]


def test_house_ids_continue_after_the_seeded_ones(client):
    async def next_house_id():
        engine = create_async_engine(settings.database_url)
        try:
            async with engine.connect() as conn:
                return (await conn.execute(text("SELECT nextval(pg_get_serial_sequence('houses', 'id'))"))).scalar()
        finally:
            await engine.dispose()

    assert asyncio.run(next_house_id()) > 10


def test_register_then_admin_assigns_house(client, admin):
    r = client.post("/api/auth/register", json={"username": "nou", "password": PASSWORD})
    assert r.status_code == 201
    user_id = r.json()["user_id"]
    token = _login(client, "nou")
    assert client.get("/api/me/house", headers=token).status_code == 403
    r = client.put(f"/api/admin/users/{user_id}", json={"house_id": 4}, headers=admin)
    assert r.status_code == 200 and r.json()["house_id"] == 4
    assert client.get("/api/me/house", headers=token).json()["id"] == 4     # same token, house re-read from DB
    assert client.put(f"/api/admin/users/{user_id}", json={"house_id": 1}, headers=admin).status_code == 400


def test_duplicates_that_pass_the_checks_are_still_a_400(client, admin, monkeypatch):
    """Two requests at once both pass the lookups; the unique constraints stop the second one."""
    users = client.get("/api/admin/users", headers=admin).json()
    user2 = next(u["user_id"] for u in users if u["username"] == "user2")

    async def nothing_found(self, *args):
        return None

    monkeypatch.setattr(UserRepository, "get_by_username", nothing_found)
    monkeypatch.setattr(UserRepository, "is_house_assigned", nothing_found)
    r = client.post("/api/auth/register", json={"username": "user1", "password": PASSWORD})
    assert r.status_code == 400 and "exista deja" in r.json()["detail"]
    r = client.put(f"/api/admin/users/{user2}", json={"house_id": 1}, headers=admin)
    assert r.status_code == 400 and "deja asignata" in r.json()["detail"]
    monkeypatch.undo()
    assert client.get(f"/api/admin/users/{user2}", headers=admin).json()["house_id"] == 2


# ---------------------------------------------------------------- security

def test_expired_token_is_rejected(client):
    user_id = client.post("/api/auth/login", json={"username": "user1", "password": PASSWORD}).json()["user_id"]
    expired = create_access_token(user_id, expires=timedelta(seconds=-1))
    assert client.get("/api/me/house", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    assert client.get("/api/me/house", headers={"Authorization": f"Bearer {expired}x"}).status_code == 401


def test_password_over_72_bytes_is_a_422_not_a_500(client):
    """72 characters with diacritics exceed bcrypt's 72-byte limit."""
    r = client.post("/api/auth/register", json={"username": "diacritice", "password": "\u0103" * 72})
    assert r.status_code == 422
    r = client.post("/api/auth/register", json={"username": "diacritice", "password": "\u0103" * 36})
    assert r.status_code == 201


def test_every_control_route_is_admin_only(client, user1):
    posts = ["/api/sim/start", "/api/sim/stop", "/api/sim/pause", "/api/sim/resume", "/api/sim/reset",
             "/api/config/reset", "/api/admin/users", "/api/admin/trades"]
    for path in posts:
        assert client.post(path, json={}, headers=user1).status_code == 403, path
    assert client.post("/api/sim/speed", json={"tick_seconds": 1}, headers=user1).status_code == 403
    for path in ["/api/trading/preferences", "/api/trading/recent", "/api/wallet/operator", "/api/admin/users",
                 "/api/sim/history"]:
        assert client.get(path, headers=user1).status_code == 403, path
    assert client.get("/api/stats/summary?house_id=2", headers=user1).status_code == 403


def test_websocket_requires_a_valid_admin_token(client, user1, admin):
    user_token = user1["Authorization"].split()[1]
    for url, reason in (("/api/admin/ws", "Token invalid sau lipsa"),
                        ("/api/admin/ws?token=nu.e.token", "Token invalid sau lipsa"),
                        (f"/api/admin/ws?token={user_token}", "Doar administratorul poate face asta")):
        with client.websocket_connect(url) as ws, pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_json()
        assert closed.value.code == 1008 and closed.value.reason == reason
    token = admin["Authorization"].split()[1]
    with client.websocket_connect(f"/api/admin/ws?token={token}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "connected" and hello["status"]["n_houses"] == 10
        assert get_engine().pool.checkedout() == 0       # an open socket holds no database connection
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


# ---------------------------------------------------------------- failed steps

def _memory_state():
    recorded = sum(int(np.isfinite(p).sum()) for p in sim.observations.prices.values())
    return ([b.soc_kwh if b else None for b in sim.batteries], sim.day, sim.t, sim.total_steps, len(sim.history),
            sim.last_result, recorded)


@pytest.mark.parametrize("error", [RuntimeError, asyncio.CancelledError])
def test_failed_or_cancelled_step_changes_nothing(client, user3, monkeypatch, error):
    """The step fails at its last write, after the batteries were already charged or discharged in memory."""
    soc_at_failure = []

    async def broken_save(session, **fields):
        soc_at_failure.append([b.soc_kwh if b else None for b in sim.batteries])
        raise error("pas intrerupt")

    async def step():
        with pytest.raises(error):
            await sim.step()

    before = _memory_state()
    soc_db = client.get("/api/houses/3/battery", headers=user3).json()["soc_kwh"]
    steps_db = client.get("/api/me/energy/today", headers=user3).json()["steps"]
    monkeypatch.setattr(sim, "_save_state", broken_save)
    client.portal.call(step)
    assert soc_at_failure[0] != before[0]
    assert _memory_state() == before
    assert client.get("/api/houses/3/battery", headers=user3).json()["soc_kwh"] == soc_db
    assert client.get("/api/me/energy/today", headers=user3).json()["steps"] == steps_db


def _run_loop(client, monkeypatch, step, done):
    """The background loop with `step` instead of the real step, stopped as soon as done() holds."""
    monkeypatch.setattr(sim, "_step", step)
    monkeypatch.setattr(sim, "config", replace(sim.config, tick_seconds=0.2))

    async def run():
        await sim.start()
        try:
            for _ in range(2000):
                if done():
                    break
                await asyncio.sleep(0.01)
        finally:
            await sim.stop()

    client.portal.call(run)


def test_loop_tries_again_after_a_failed_step(client, monkeypatch):
    real_step, steps, errors = sim._step, sim.total_steps, []

    async def fails_once():
        errors.append(sim.last_error)
        if len(errors) == 1:
            raise RuntimeError("conexiune pierduta")
        return await real_step()

    _run_loop(client, monkeypatch, fails_once, lambda: sim.total_steps >= steps + 2)
    assert sim.total_steps >= steps + 2 and not sim.paused
    assert errors[:2] == [None, "conexiune pierduta"] and sim.last_error is None


def test_loop_pauses_after_five_failed_steps_in_a_row(client, admin, monkeypatch):
    calls = []

    async def always_fails():
        calls.append(sim.paused)
        raise RuntimeError("baza de date oprita")

    _run_loop(client, monkeypatch, always_fails, lambda: sim.paused)
    assert calls == [False] * 5
    status = client.get("/api/sim/status", headers=admin).json()
    assert status["paused"] is True and status["last_error"] == "baza de date oprita"
    status = client.post("/api/sim/resume", headers=admin).json()["status"]
    assert status["paused"] is False and status["last_error"] is None


def test_reset_restores_initial_state(client, admin, user3):
    r = client.post("/api/sim/reset", headers=admin)
    assert r.status_code == 200 and r.json()["status"]["total_steps"] == 0
    assert client.get("/api/wallet/3", headers=user3).json()["balance_lei"] == 100.0
    assert client.get("/api/houses/3/battery", headers=user3).json()["soc_percent"] == 50.0
    assert client.get("/api/me/energy/today", headers=user3).json()["steps"] == 0


def test_stats_comparison_uses_romanian_month_names(client, user3):
    r = client.get("/api/stats/comparison", headers=user3)
    assert r.status_code == 200, r.text
    body = r.json()
    months = ("ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
              "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie")
    for key in ("current_month", "previous_month"):
        name, year = body[key].split()
        assert name in months and year.isdigit()


# moves the clock into the next day, so it stays the last test of the module
def test_prices_switch_to_the_new_day_at_midnight(client, admin):
    status = client.get("/api/sim/status", headers=admin).json()
    for _ in range(status["steps_per_day"] - status["step_of_day"]):
        assert client.post("/api/sim/step", headers=admin).status_code == 200
    status = client.get("/api/sim/status", headers=admin).json()
    prices = client.get("/api/sim/prices", headers=admin).json()
    assert status["step_of_day"] == 0 and prices["date"] == status["sim_date"]
    step = client.post("/api/sim/step", headers=admin).json()
    assert step["price"]["import"] == pytest.approx(prices["prices"][0]["price_import"], abs=1e-4)
