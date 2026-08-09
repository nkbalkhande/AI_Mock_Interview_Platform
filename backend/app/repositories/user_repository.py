"""Repository for the ``users`` table."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.user_role import UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email (case-insensitive), with roles eager-loaded.

        Matches the ``lower(email)`` unique index on ``users`` so lookups line
        up with the DB's uniqueness guarantee.
        """
        stmt = (
            select(User)
            .where(func.lower(User.email) == email.strip().lower())
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_roles(
        self, user_id: uuid.UUID, *, with_profile: bool = False
    ) -> User | None:
        """Fetch a user by id with roles (and optionally profile) eager-loaded.

        Used by the auth dependency so route handlers get a ``User`` whose
        ``user_roles[].role.name`` is already populated for RBAC checks
        without triggering lazy-load queries inside request handling.
        """
        options = [selectinload(User.user_roles).selectinload(UserRole.role)]
        if with_profile:
            options.append(selectinload(User.profile))
        stmt = select(User).where(User.id == user_id).options(*options)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
