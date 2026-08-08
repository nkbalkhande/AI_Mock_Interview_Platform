"""Database engine and session factory (Singleton Engine + per-request Session).

We create exactly **one** async ``Engine`` for the whole process. The engine
owns the connection pool. Individual requests get their own short-lived
``AsyncSession`` from the session factory — never a shared session.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# Single application-wide engine (manages the connection pool).
engine: AsyncEngine = create_async_engine(
    settings.async_database_url,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,
    future=True,
)

# Factory that produces new AsyncSession objects bound to the engine above.
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def dispose_engine() -> None:
    """Dispose the engine and close all pooled connections (on shutdown)."""
    await engine.dispose()
