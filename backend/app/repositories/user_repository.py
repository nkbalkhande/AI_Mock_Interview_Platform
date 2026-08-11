"""Repository for the ``users`` table."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import String, func, or_, select
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.models.user import User
from app.models.user_profile import UserProfile
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
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role),
                selectinload(User.profile),
            )
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

    # ------------------------------------------------------------------
    # Admin-scoped queries
    # ------------------------------------------------------------------

    async def count_filtered(
        self,
        *,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> int:
        stmt = select(func.count(User.id))
        stmt = self._apply_filters(stmt, search=search, role=role, is_active=is_active)
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> Sequence[User]:
        offset = (page - 1) * page_size
        stmt = (
            select(User)
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role),
                selectinload(User.profile),
            )
        )
        stmt = self._apply_filters(stmt, search=search, role=role, is_active=is_active)
        stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def get_detail(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(
                selectinload(User.user_roles).selectinload(UserRole.role),
                selectinload(User.profile),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def count_candidates(self) -> int:
        stmt = (
            select(func.count(func.distinct(User.id)))
            .select_from(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(Role.name == "CANDIDATE")
        )
        return int((await self.session.execute(stmt)).scalar_one())

    @staticmethod
    def _apply_filters(stmt, *, search, role, is_active):  # noqa: ANN001, ANN205
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                )
            )
        if role:
            stmt = stmt.join(
                UserRole, User.id == UserRole.user_id, isouter=False
            ).join(Role, UserRole.role_id == Role.id).where(
                Role.name == role
            )
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        return stmt
