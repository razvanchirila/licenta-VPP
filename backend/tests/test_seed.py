"""scripts/seed.py demo on the PostgreSQL test database: DEMO_PASSWORD and password rotation."""
import asyncio
import importlib.util
import os
from pathlib import Path

import pytest
from conftest import api_database_url, recreate_tables

os.environ.update({
    "DATABASE_URL": api_database_url(),
    "JWT_SECRET_KEY": "test-secret-key-not-for-production",
})


@pytest.fixture(scope="module", autouse=True)
def _imports():
    """Imported when the first test runs, after every module was collected: app.settings is read only once
    and test_api.py sets its own environment at import time."""
    global close_db, get_session_context, UserRepository, verify_password, create_user, seed
    from app.db.database import close_db, get_session_context
    from app.db.repositories import UserRepository
    from app.services.auth import verify_password
    from app.services.users import create_user

    spec = importlib.util.spec_from_file_location("seed", Path(__file__).parents[1] / "scripts" / "seed.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)


DEMO = ["admin"] + [f"user{i}" for i in range(1, 11)]


def _seed(*args):
    assert seed.main(["seed.py", *args]) == 0


async def _users(names):
    async with get_session_context() as session:
        repo = UserRepository(session)
        found = {name: await repo.get_by_username(name) for name in names}
    await close_db()
    return found


def _passwords_match(names, password):
    users = asyncio.run(_users(names))
    return {name: verify_password(password, u.password_hash) for name, u in users.items()}


async def _add_other_user():
    async with get_session_context() as session:
        await create_user(session, "ion", "parola-ion", None, False)
    await close_db()


@pytest.fixture
def empty_db():
    asyncio.run(recreate_tables())
    asyncio.run(close_db())


def test_demo_password_defaults_to_123(empty_db, monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    _seed("demo")
    assert all(_passwords_match(DEMO, "123").values())


def test_demo_password_from_env_and_argument(monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD", "din-mediu")
    assert {p for _, p, _, _ in seed.parse(["seed.py", "demo"])} == {"din-mediu"}
    assert {p for _, p, _, _ in seed.parse(["seed.py", "demo", "argument"])} == {"argument"}
    monkeypatch.setenv("DEMO_PASSWORD", "")
    assert {p for _, p, _, _ in seed.parse(["seed.py", "demo"])} == {"123"}


def test_changing_demo_password_rotates_only_demo_accounts(empty_db, monkeypatch):
    monkeypatch.delenv("DEMO_PASSWORD", raising=False)
    _seed("demo")
    asyncio.run(_add_other_user())
    before = asyncio.run(_users(DEMO))

    monkeypatch.setenv("DEMO_PASSWORD", "parola-noua-7")
    _seed("demo")

    after = asyncio.run(_users(DEMO + ["ion"]))
    assert all(_passwords_match(DEMO, "parola-noua-7").values())
    assert not any(_passwords_match(DEMO, "123").values())
    assert verify_password("parola-ion", after["ion"].password_hash)
    for name in DEMO:
        assert (after[name].id, after[name].house_id, after[name].is_admin) == \
               (before[name].id, before[name].house_id, before[name].is_admin)


def test_same_password_keeps_the_hash(empty_db, monkeypatch):
    monkeypatch.setenv("DEMO_PASSWORD", "aceeasi")
    _seed("demo")
    first = {n: u.password_hash for n, u in asyncio.run(_users(DEMO)).items()}
    _seed("demo")
    assert {n: u.password_hash for n, u in asyncio.run(_users(DEMO)).items()} == first


def test_single_account_commands_do_not_reset_passwords(empty_db):
    _seed("admin", "sef", "prima")
    _seed("admin", "sef", "a-doua")
    assert _passwords_match(["sef"], "prima") == {"sef": True}
