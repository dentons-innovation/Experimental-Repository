"""SQLAlchemy async engine and session factory.

Design notes:
- Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).
- Automatically tunes engine arguments based on driver.
- For SQLite, enables foreign key constraints and creates all tables on startup.
- expire_on_commit=False prevents lazy-load after commit in async context.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
    """Enable SQLite foreign key support on every new connection."""
    module_name = getattr(type(dbapi_connection), "__module__", "")
    if "sqlite" in module_name:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def build_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create the SQLAlchemy async engine from settings."""
    s = settings or get_settings()
    url = s.test_database_url if s.is_test else s.database_url

    if url.startswith("sqlite"):
        return create_async_engine(
            url,
            echo=s.debug,
            future=True,
            connect_args={"check_same_thread": False},
        )

    return create_async_engine(
        url,
        pool_size=s.db_pool_size,
        max_overflow=s.db_max_overflow,
        pool_timeout=s.db_pool_timeout,
        pool_recycle=s.db_pool_recycle,
        pool_pre_ping=True,  # Reconnect after network blips
        echo=s.debug,
        future=True,
    )


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        engine,
        expire_on_commit=False,  # Required in async context
        autoflush=False,
        autocommit=False,
        class_=AsyncSession,
    )


# Module-level singletons (created once per process)
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine  # noqa: PLW0603
    if _engine is None:
        _engine = build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory  # noqa: PLW0603
    if _session_factory is None:
        _session_factory = build_session_factory(get_engine())
    return _session_factory


async def init_db() -> None:
    """Create all tables in the database if they do not already exist."""
    from app.domain.models import Base

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, Any]:
    """FastAPI dependency that yields a database session per request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
