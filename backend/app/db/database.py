import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import settings

from .models import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
        logger.info("Database engine created for %s", _engine.url.render_as_string(hide_password=True))
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), class_=AsyncSession, expire_on_commit=False,
                                              autoflush=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Databases created before the device catalog had schedules per catalog row and no household profile:
# create_all leaves existing tables alone, so their columns are brought in line here (idempotent).
SCHEMA_UPGRADE = (
    "ALTER TABLE houses ADD COLUMN IF NOT EXISTS description VARCHAR(200) NOT NULL DEFAULT ''",
    "ALTER TABLE houses ADD COLUMN IF NOT EXISTS people INTEGER NOT NULL DEFAULT 1",
    "ALTER TABLE houses ADD COLUMN IF NOT EXISTS home_daytime BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE houses ADD COLUMN IF NOT EXISTS heating VARCHAR(50) NOT NULL DEFAULT 'gaz'",
    "ALTER TABLE houses ADD COLUMN IF NOT EXISTS insulation VARCHAR(10) NOT NULL DEFAULT 'medie'",
    "ALTER TABLE devices ADD COLUMN IF NOT EXISTS program TEXT NOT NULL DEFAULT '[]'",
    "ALTER TABLE devices DROP COLUMN IF EXISTS hours_per_day, DROP COLUMN IF EXISTS cycles_per_week, "
    "DROP COLUMN IF EXISTS cycle_minutes, DROP COLUMN IF EXISTS interval, DROP COLUMN IF EXISTS season",
)


async def init_db() -> None:
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        for statement in SCHEMA_UPGRADE:
            await conn.execute(text(statement))


async def close_db() -> None:
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
