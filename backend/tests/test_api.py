"""
End-to-end tests of the HTTP API on a temporary SQLite database.
The simulation loop is loaded but not started; steps are triggered by hand.
"""
import asyncio
import os
import tempfile
from datetime import timedelta

import pytest

_TMP = tempfile.mkdtemp(prefix="vpp-test-")
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///" + os.path.join(_TMP, "test.db").replace("\\", "/"),
    "JWT_SECRET_KEY": "test-secret-key-not-for-production",
    "SIM_AUTOSTART": "false",
    "SIM_START_DATE": "2025-06-01",
    "SIM_CONTROLLER": "reguli",
    "INITIAL_WALLET_LEI": "100",
})

from fastapi.testclient import TestClient  # noqa: E402
from starlette.websockets import WebSocketDisconnect  # noqa: E402

from app.db.database import close_db, get_session_context, init_db  # noqa: E402
from app.db.init_data import seed_houses  # noqa: E402
from app.services import settlement  # noqa: E402
from app.services.auth import create_access_token  # noqa: E402
from app.services.users import create_user  # noqa: E402
from app.settings import BACKEND_DIR, _database_url  # noqa: E402
from main import app  # noqa: E402

PASSWORD = "parola123"


async def _seed():
    await init_db()
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


def test_dashboard_is_served_with_csp(client):
    """The operator dashboard is static, same-origin, and forbids inline scripts via CSP."""
    r = client.get("/")
    assert r.status_code == 200 and "text/html" in r.headers["content-type"]
    assert "Content-Security-Policy" in r.text and "script-src 'self'" in r.text
    assert "onclick=" not in r.text and "<script>" not in r.text
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/styles.css").status_code == 200


def test_login_rejects_bad_password(client):
    r = client.post("/api/auth/login", json={"username": "user1", "password": "gresit"})
    assert r.status_code == 401


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
    assert dev["accumulated_energy_kwh"] == pytest.approx(0.2 * 0.25)   # 200 W for 15 minutes
    assert dev["current_power_kw"] == pytest.approx(0.2) and dev["schedule"] is None
    today = client.get("/api/me/energy/today", headers=user3).json()
    assert today["steps"] == 1 and today["device_kwh"] == pytest.approx(house3["load_kw"] * 0.25, abs=1e-3)
    stats = client.get("/api/stats/summary?period=day", headers=user3).json()
    assert stats["total_kwh"] == pytest.approx(house3["load_kw"] * 0.25, abs=1e-3)   # energy_logs add up to the load
    soc_after = client.get("/api/houses/3/battery", headers=user3).json()["soc_kwh"]
    assert soc_after == pytest.approx(house3["soc_kwh"], abs=1e-3)
    assert soc_after != soc_before or house3["ch_kw"] == 0 == house3["dis_kw"]
    status = client.get("/api/sim/status", headers=user3).json()
    assert status["total_steps"] == 1 and status["sim_time"] == "00:15"


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


def test_settings_change_reaches_the_simulation(client, user3, admin):
    r = client.put("/api/me/settings", json={"mode": "Profit", "backup_reserve_percent": 30}, headers=user3)
    assert r.status_code == 200 and r.json()["mode"] == "Profit" and r.json()["backup_reserve_percent"] == 30
    step = client.post("/api/sim/step", headers=admin).json()
    house3 = next(h for h in step["houses"] if h["id"] == 3)
    assert house3["mode"] == "Profit"
    assert house3["soc_kwh"] >= 0.3 * 16 - 1e-6          # one SE-F16 module


def test_config_switches_controller_to_mpc(client, admin, user1):
    r = client.put("/api/config", json={"controller": "mpc"}, headers=admin)
    assert r.status_code == 200 and r.json()["config"]["controller"] == "mpc"
    step = client.post("/api/sim/step", headers=admin).json()
    assert step["controller"] == "mpc"
    assert client.get("/api/config", headers=user1).json()["controller"] == "mpc"
    assert client.post("/api/config/reset", headers=admin).json()["config"]["controller"] == "reguli"


def test_prices_and_history(client, user1):
    prices = client.get("/api/sim/prices", headers=user1).json()
    assert len(prices["prices"]) == 96 and prices["prices"][0]["price_import"] > prices["prices"][0]["price_p2p"]
    history = client.get("/api/sim/history?limit=2", headers=user1).json()
    assert history["count"] == 2 and "community" in history["steps"][-1]


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
    for period, minutes in (("day", 15), ("week", 180), ("month", 1440)):
        r = client.get(f"/api/me/energy/chart?period={period}", headers=user1)
        assert r.status_code == 200 and r.json()["interval_minutes"] == minutes, period
    assert client.get("/api/me/energy/chart?date=2025-13-40", headers=user1).status_code == 400
    impact = client.get("/api/me/energy/impact", headers=user1).json()
    assert impact["monthly_savings"][-1]["current"] is True and len(impact["monthly_savings"]) == 6


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
    for path in ["/api/trading/preferences", "/api/trading/recent", "/api/wallet/operator", "/api/admin/users"]:
        assert client.get(path, headers=user1).status_code == 403, path
    assert client.get("/api/stats/summary?house_id=2", headers=user1).status_code == 403


def test_websocket_requires_a_valid_token(client, user1):
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/admin/ws"):
            pass
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/admin/ws?token=nu.e.token"):
            pass
    token = user1["Authorization"].split()[1]
    with client.websocket_connect(f"/api/admin/ws?token={token}") as ws:
        hello = ws.receive_json()
        assert hello["type"] == "connected" and hello["status"]["n_houses"] == 10
        ws.send_text("ping")
        assert ws.receive_text() == "pong"


# ---------------------------------------------------------------- settings

def test_relative_sqlite_path_resolves_against_backend_dir(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./vpp.db")
    assert _database_url() == "sqlite+aiosqlite:///" + (BACKEND_DIR / "vpp.db").resolve().as_posix()
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///data/x.db")
    assert _database_url().endswith("/backend/data/x.db")


def test_absolute_and_non_sqlite_urls_are_left_alone(monkeypatch):
    for url in ("sqlite+aiosqlite:///C:/tmp/a.db", "sqlite+aiosqlite:////tmp/a.db", "sqlite+aiosqlite:///:memory:",
                "postgresql+asyncpg://u:p@host/db"):
        monkeypatch.setenv("DATABASE_URL", url)
        assert _database_url() == url


def test_reset_restores_initial_state(client, admin, user3):
    r = client.post("/api/sim/reset", headers=admin)
    assert r.status_code == 200 and r.json()["status"]["total_steps"] == 0
    assert client.get("/api/wallet/3", headers=user3).json()["balance_lei"] == 100.0
    assert client.get("/api/houses/3/battery", headers=user3).json()["soc_percent"] == 50.0
    assert client.get("/api/me/energy/today", headers=user3).json()["steps"] == 0
