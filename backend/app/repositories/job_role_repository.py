"""Read access for the active interview role catalog."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.job_role import JobRole
from app.repositories.base import BaseRepository


class JobRoleRepository(BaseRepository[JobRole]):
    model = JobRole

    async def list_active(self) -> Sequence[JobRole]:
        result = await self.session.execute(
            select(JobRole)
            .where(JobRole.is_active.is_(True))
            .order_by(JobRole.name)
        )
        return result.scalars().all()

    async def get_active(self, role_id: uuid.UUID) -> JobRole | None:
        result = await self.session.execute(
            select(JobRole).where(
                JobRole.id == role_id,
                JobRole.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()
