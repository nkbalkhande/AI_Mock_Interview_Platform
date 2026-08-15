"""Repository for the ``interviews`` table.

Candidate-scoped queries take a ``candidate_id`` filter so candidates never
see other candidates' data.  Admin-scoped queries (prefixed ``admin_``) have
no candidate filter and can see all interviews.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from datetime import datetime, timezone

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import selectinload

from app.models.interview import Interview
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.repositories.base import BaseRepository

# Statuses shown as "upcoming" in the candidate's dashboard. Includes
# IN_PROGRESS so a candidate who already joined can rejoin from the list.
# DRAFT is admin-side and shouldn't leak before an admin publishes it.
_UPCOMING_STATUSES: tuple[str, ...] = (
    "ASSIGNED",
    "SCHEDULED",
    "AVAILABLE",
    "IN_PROGRESS",
    "RESCHEDULED",
)
_STARTABLE_ASSIGNED_STATUSES: tuple[str, ...] = (
    "ASSIGNED",
    "SCHEDULED",
    "AVAILABLE",
    "RESCHEDULED",
)

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
            .options(
                selectinload(Interview.resume_version),
                selectinload(Interview.assigned_by_user),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_owned_for_start(
        self, interview_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Interview | None:
        """Lock an owned assigned interview so start/resume is serialized.

        Eager-loads the snapshotted resume and existing sessions (with
        questions + answers) so ``start_assigned`` can resume without a
        lazy load under asyncpg. ``None`` means missing or not yours.
        """
        stmt = (
            select(Interview)
            .where(
                Interview.id == interview_id,
                Interview.candidate_id == candidate_id,
            )
            .options(
                selectinload(Interview.resume_version),
                selectinload(Interview.sessions)
                .selectinload(InterviewSession.questions)
                .selectinload(InterviewQuestion.answer),
            )
            .with_for_update(of=Interview)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def expire_overdue_assigned(self) -> int:
        """Mark assigned interviews whose access window closed as EXPIRED.

        Skips interviews that already have a started/submitted session so an
        in-progress attempt is never treated as a no-show.
        """
        now = datetime.now(timezone.utc)
        started = select(InterviewSession.interview_id).where(
            InterviewSession.status.in_(
                (
                    "IN_PROGRESS",
                    "PAUSED",
                    "SUBMITTED",
                    "EVALUATING",
                    "EVALUATED",
                    "COMPLETED",
                )
            )
        )
        stmt = (
            update(Interview)
            .where(
                Interview.interview_type == "ASSIGNED",
                Interview.status.in_(_STARTABLE_ASSIGNED_STATUSES),
                Interview.access_end_at.is_not(None),
                Interview.access_end_at < now,
                Interview.id.not_in(started),
            )
            .values(status="EXPIRED")
        )
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)

    async def has_schedule_conflict(
        self,
        *,
        candidate_id: uuid.UUID,
        access_start: datetime,
        access_end: datetime,
        exclude_interview_id: uuid.UUID,
    ) -> bool:
        """True when another active assigned interview overlaps the window."""
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == candidate_id,
            Interview.id != exclude_interview_id,
            Interview.interview_type == "ASSIGNED",
            Interview.status.in_((*_STARTABLE_ASSIGNED_STATUSES, "IN_PROGRESS")),
            Interview.access_start_at.is_not(None),
            Interview.access_end_at.is_not(None),
            Interview.access_start_at < access_end,
            Interview.access_end_at > access_start,
        )
        return int((await self.session.execute(stmt)).scalar_one()) > 0

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

    async def count_completed_by_type(
        self, candidate_id: uuid.UUID, *, interview_type: str
    ) -> int:
        """Count completed interviews of a specific type for a candidate."""
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == candidate_id,
            Interview.interview_type == interview_type,
            Interview.status.in_(_COMPLETED_STATUSES),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_completed_paginated(
        self,
        candidate_id: uuid.UUID,
        *,
        interview_type: str,
        page: int = 1,
        page_size: int = 20,
    ) -> Sequence[Interview]:
        """Paginated list of completed interviews for the candidate."""
        offset = (page - 1) * page_size
        stmt = (
            select(Interview)
            .where(
                Interview.candidate_id == candidate_id,
                Interview.interview_type == interview_type,
                Interview.status.in_(_COMPLETED_STATUSES),
            )
            .order_by(Interview.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    # ------------------------------------------------------------------
    # Candidate interview history (all statuses, not just completed)
    # ------------------------------------------------------------------

    _HISTORY_EXCLUDED_STATUSES: tuple[str, ...] = ("DRAFT",)

    async def count_history(
        self,
        candidate_id: uuid.UUID,
        *,
        status_filter: str | None = None,
        type_filter: str | None = None,
    ) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == candidate_id,
            Interview.status.not_in(self._HISTORY_EXCLUDED_STATUSES),
        )
        stmt = self._apply_history_filters(stmt, status_filter=status_filter, type_filter=type_filter)
        return int((await self.session.execute(stmt)).scalar_one())

    async def list_history_paginated(
        self,
        candidate_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        type_filter: str | None = None,
    ) -> Sequence[Interview]:
        offset = (page - 1) * page_size
        stmt = (
            select(Interview)
            .where(
                Interview.candidate_id == candidate_id,
                Interview.status.not_in(self._HISTORY_EXCLUDED_STATUSES),
            )
            .options(selectinload(Interview.sessions))
            .order_by(Interview.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        stmt = self._apply_history_filters(stmt, status_filter=status_filter, type_filter=type_filter)
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    def _apply_history_filters(self, stmt, *, status_filter, type_filter):  # noqa: ANN001, ANN202
        if type_filter == "practice":
            stmt = stmt.where(Interview.interview_type == "PRACTICE")
        elif type_filter == "assigned":
            stmt = stmt.where(Interview.interview_type == "ASSIGNED")

        if status_filter == "completed":
            stmt = stmt.where(Interview.status.in_(_COMPLETED_STATUSES))
        elif status_filter == "in_progress":
            stmt = stmt.where(Interview.status == "IN_PROGRESS")
        elif status_filter == "evaluating":
            stmt = stmt.where(Interview.status.in_(("SUBMITTED", "AI_EVALUATED", "ADMIN_REVIEW")))
        elif status_filter == "incomplete":
            stmt = stmt.where(Interview.status.in_(("CANCELLED", "EXPIRED")))
        return stmt

    # ------------------------------------------------------------------
    # Admin-scoped queries
    # ------------------------------------------------------------------

    async def admin_count_all(self) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.status.not_in(("DRAFT",))
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_count_completed(self) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.status.in_(_COMPLETED_STATUSES)
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_count_by_statuses(self, statuses: Sequence[str]) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.status.in_(tuple(statuses))
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_count_scheduled_upcoming(self) -> int:
        now = func.now()
        stmt = select(func.count(Interview.id)).where(
            Interview.status.in_(
                ("ASSIGNED", "SCHEDULED", "AVAILABLE", "RESCHEDULED")
            ),
            Interview.scheduled_at.is_not(None),
            Interview.scheduled_at > now,
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_count_filtered(
        self,
        *,
        status: str | None = None,
        interview_type: str | None = None,
        search: str | None = None,
    ) -> int:
        stmt = select(func.count(Interview.id)).select_from(Interview).where(
            Interview.status.not_in(("DRAFT",))
        )
        stmt = self._admin_apply_filters(
            stmt, status=status, interview_type=interview_type, search=search
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        interview_type: str | None = None,
        search: str | None = None,
    ) -> Sequence[Interview]:
        offset = (page - 1) * page_size
        stmt = (
            select(Interview)
            .where(Interview.status.not_in(("DRAFT",)))
            .options(
                selectinload(Interview.candidate),
                selectinload(Interview.assigned_by_user),
            )
        )
        stmt = self._admin_apply_filters(
            stmt, status=status, interview_type=interview_type, search=search
        )
        stmt = stmt.order_by(Interview.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def admin_get_detail(self, interview_id: uuid.UUID) -> Interview | None:
        stmt = (
            select(Interview)
            .where(Interview.id == interview_id)
            .options(
                selectinload(Interview.candidate),
                selectinload(Interview.assigned_by_user),
                selectinload(Interview.rescheduled_by_user),
                selectinload(Interview.resume_version),
                selectinload(Interview.events),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def admin_count_for_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == user_id,
            Interview.status.not_in(("DRAFT",)),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_count_for_user_by_type(
        self, user_id: uuid.UUID, *, interview_type: str
    ) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == user_id,
            Interview.interview_type == interview_type,
            Interview.status.not_in(("DRAFT",)),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_count_for_user_completed(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(Interview.id)).where(
            Interview.candidate_id == user_id,
            Interview.status.in_(_COMPLETED_STATUSES),
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_list_for_user(
        self,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Sequence[Interview]:
        offset = (page - 1) * page_size
        stmt = (
            select(Interview)
            .where(
                Interview.candidate_id == user_id,
                Interview.status.not_in(("DRAFT",)),
            )
            .order_by(Interview.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    def _admin_apply_filters(self, stmt, *, status, interview_type, search):  # noqa: ANN001, ANN202
        if status:
            # Support grouped quick-filters from the admin UI.
            if status == "IN_PROGRESS_GROUP":
                stmt = stmt.where(
                    Interview.status.in_(("IN_PROGRESS", "AVAILABLE"))
                )
            elif status == "COMPLETED_GROUP":
                stmt = stmt.where(Interview.status.in_(_COMPLETED_STATUSES))
            elif status == "CANCELLED_GROUP":
                stmt = stmt.where(Interview.status == "CANCELLED")
            elif status == "MISSED_GROUP":
                stmt = stmt.where(Interview.status == "EXPIRED")
            else:
                stmt = stmt.where(Interview.status == status)
        if interview_type:
            stmt = stmt.where(Interview.interview_type == interview_type)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.join(
                User, Interview.candidate_id == User.id, isouter=True
            ).where(
                or_(
                    User.full_name.ilike(pattern),
                    User.email.ilike(pattern),
                    Interview.role_name_snapshot.ilike(pattern),
                )
            )
        return stmt
