"""Repository for the ``interviews`` table.

Read-only queries scoped to a candidate — the dashboard needs to summarise a
user's interviews without leaking anyone else's data, so every method here
takes a ``candidate_id`` filter and never returns other candidates' rows.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.interview import Interview
from app.repositories.base import BaseRepository

# Statuses shown as "upcoming" in the candidate's dashboard. Excludes anything
# already started/finished/cancelled/expired. DRAFT is admin-side and shouldn't
# leak to candidates before an admin publishes it (moves it to ASSIGNED+).
_UPCOMING_STATUSES: tuple[str, ...] = ("ASSIGNED", "SCHEDULED", "AVAILABLE")

# Statuses that represent a submitted interview (candidate side is done).
_COMPLETED_STATUSES: tuple[str, ...] = (
    "SUBMITTED",
    "AI_EVALUATED",
    "ADMIN_REVIEW",
    "COMPLETED",
)


class InterviewRepository(BaseRepository[Interview]):
    model = Interview

    async def count_by_type(
        self, candidate_id: uuid.UUID, *, interview_type: str
    ) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == candidate_id,
            Interview.interview_type == interview_type,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_upcoming_assigned(self, candidate_id: uuid.UUID) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == candidate_id,
            Interview.interview_type == "ASSIGNED",
            Interview.status.in_(_UPCOMING_STATUSES),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def count_completed(self, candidate_id: uuid.UUID) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == candidate_id,
            Interview.status.in_(_COMPLETED_STATUSES),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_upcoming(
        self, candidate_id: uuid.UUID, *, limit: int = 20
    ) -> Sequence[Interview]:
        """List an candidate's upcoming assigned interviews (soonest first)."""
        stmt = (
            select(Interview)
            .where(
                Interview.candidate_id == candidate_id,
                Interview.interview_type == "ASSIGNED",
                Interview.status.in_(_UPCOMING_STATUSES),
            )
            .order_by(Interview.scheduled_at.asc().nulls_last())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_owned_by_candidate(
        self, interview_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Interview | None:
        """Fetch an interview only if it belongs to ``candidate_id``.

        Returning ``None`` when the row exists but belongs to someone else
        gives the caller a single code path for "not found or not yours" —
        letting API handlers respond with a uniform 404 (never leak the
        existence of another user's interview via a 403).
        """
        stmt = (
            select(Interview)
            .where(
                Interview.id == interview_id,
                Interview.candidate_id == candidate_id,
            )
            .options(selectinload(Interview.resume_version))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_recent_completed(
        self,
        candidate_id: uuid.UUID,
        *,
        limit: int = 5,
        interview_type: str | None = None,
    ) -> Sequence[Interview]:
        """Most recently completed interviews for the candidate.

        Filters by ``interview_type`` if provided (``"PRACTICE"`` or
        ``"ASSIGNED"``). Ordered by ``updated_at`` DESC — ``updated_at`` bumps
        each time status transitions, so it's the most reliable proxy for
        "recently completed" without joining sessions.
        """
        stmt = select(Interview).where(
            Interview.candidate_id == candidate_id,
            Interview.status.in_(_COMPLETED_STATUSES),
        )
        if interview_type is not None:
            stmt = stmt.where(Interview.interview_type == interview_type)
        stmt = stmt.order_by(Interview.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()
