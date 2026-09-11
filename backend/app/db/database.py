"""Database connection manager for VPP Simulator."""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from .config import DatabaseConfig
from .models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_async_engine = None
_async_session_factory = None


def get_engine():
    """Get or create the async database engine."""
    global _async_engine
    
    if _async_engine is None:
        _async_engine = create_async_engine(
            DatabaseConfig.get_async_url(),
            pool_size=DatabaseConfig.POOL_SIZE,
            max_overflow=DatabaseConfig.MAX_OVERFLOW,
            pool_timeout=DatabaseConfig.POOL_TIMEOUT,
            pool_recycle=DatabaseConfig.POOL_RECYCLE,
            echo=DatabaseConfig.ECHO_SQL,
        )
        logger.info(f"Created async database engine for {DatabaseConfig.DB_HOST}:{DatabaseConfig.DB_PORT}")
    
    return _async_engine


def get_session_factory():
    """Get or create the async session factory."""
    global _async_session_factory
    
    if _async_session_factory is None:
        engine = get_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        logger.info("Created async session factory")
    
    return _async_session_factory



async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting a database session.
    
    Usage:
        @app.get("/items")
        async def get_items(session: AsyncSession = Depends(get_session)):
            ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting a database session outside of FastAPI.
    
    Usage:
        async with get_session_context() as session:
            ...
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def create_database_if_not_exists():
    """Create the database if it doesn't exist (sync operation for startup)."""
    from sqlalchemy import create_engine as create_sync_engine
    
    # Connect to MySQL server without specifying database
    server_url = DatabaseConfig.get_server_url()
    engine = create_sync_engine(server_url, echo=DatabaseConfig.ECHO_SQL)
    
    with engine.connect() as conn:
        # Check if database exists
        result = conn.execute(
            text(f"SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = '{DatabaseConfig.DB_NAME}'")
        )
        exists = result.fetchone() is not None
        
        if not exists:
            conn.execute(text(f"CREATE DATABASE {DatabaseConfig.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
            logger.info(f"Created database: {DatabaseConfig.DB_NAME}")
        else:
            logger.info(f"Database already exists: {DatabaseConfig.DB_NAME}")
    
    engine.dispose()


async def init_db():
    """Initialize database - create all tables."""
    # First ensure database exists
    create_database_if_not_exists()
    
    # Create all tables using async engine
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database tables created successfully")


async def close_db():
    """Close database connections."""
    global _async_engine, _async_session_factory
    
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Database connections closed")
