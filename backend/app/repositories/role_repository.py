"""Repository for the ``roles`` table."""

from __future__ import annotations

from sqlalchemy import select

from app.models.role import Role
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[Role]):
    model = Role

    async def get_by_name(self, name: str) -> Role | None:
        """Fetch a role by its unique ``name`` (e.g. ``"CANDIDATE"``)."""
        stmt = select(Role).where(Role.name == name)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
