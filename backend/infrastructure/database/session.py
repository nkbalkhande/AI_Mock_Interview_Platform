"""Request-scoped database session provisioning.

``get_db`` is the FastAPI dependency that yields a fresh ``AsyncSession`` per
request and guarantees it is closed afterwards. It does not commit for you —
services / the Unit of Work own transaction boundaries.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield a session and always close it."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def session_scope() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for a transactional session outside the request cycle
    (scripts, workers, seeders). Commits on success, rolls back on error.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
