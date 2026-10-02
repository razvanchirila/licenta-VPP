import asyncio
import functools
import os
from datetime import date

import asyncpg
import numpy as np
import pytest
from sqlalchemy import make_url

from vpp_core.scenario import Scenario

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://vpp:vpp@localhost:15432/vpp_test").strip()
NO_SERVER = "PostgreSQL nu ruleaza: docker compose up -d db"


async def _create_database_if_missing(url) -> None:
    conn = await asyncpg.connect(host=url.host, port=url.port or 5432, user=url.username, password=url.password,
                                 database="postgres", timeout=3)
    try:
        if not await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", url.database):
            await conn.execute('CREATE DATABASE "{}"'.format(url.database.replace('"', '""')))
    except asyncpg.DuplicateDatabaseError:
        pass
    finally:
        await conn.close()


@functools.cache
def _server_is_up(url: str) -> bool:
    try:
        asyncio.run(_create_database_if_missing(make_url(url)))
    except (OSError, TimeoutError, asyncpg.CannotConnectNowError):
        return False
    return True


def api_database_url() -> str:
    """TEST_DATABASE_URL, created on the server if missing; the calling test module is skipped when PostgreSQL
    is not running. The API tests drop every table first, so the database must have "test" in its name."""
    if "test" not in (make_url(TEST_DATABASE_URL).database or ""):
        raise RuntimeError("TEST_DATABASE_URL trebuie sa fie o baza de test (numele contine 'test'): "
                           "testele sterg toate tabelele")
    if not _server_is_up(TEST_DATABASE_URL):
        pytest.skip(NO_SERVER, allow_module_level=True)
    return TEST_DATABASE_URL


async def recreate_tables() -> None:
    from app.db.database import get_engine
    from app.db.models import Base

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


def make_scenario(pv, crit, flex=None, dt_h=1.0, price_import=None, price_export=None, price_p2p=None):
    """Scenario from explicit arrays. pv/crit/flex: (H, T); prices: (T,)."""
    pv = np.asarray(pv, dtype=float)
    crit = np.asarray(crit, dtype=float)
    flex = np.zeros_like(crit) if flex is None else np.asarray(flex, dtype=float)
    T = pv.shape[1]
    price_import = np.full(T, 1.0) if price_import is None else np.asarray(price_import, dtype=float)
    price_export = np.full(T, 0.3) if price_export is None else np.asarray(price_export, dtype=float)
    price_p2p = 0.7 * price_import if price_p2p is None else np.asarray(price_p2p, dtype=float)
    return Scenario(
        dt_h=dt_h, start=date(2025, 6, 1), pv_kw=pv, load_crit_kw=crit, load_flex_kw=flex,
        price_import=price_import, price_export=price_export, price_p2p=price_p2p,
    )


def const(H, T, value):
    return np.full((H, T), float(value))
