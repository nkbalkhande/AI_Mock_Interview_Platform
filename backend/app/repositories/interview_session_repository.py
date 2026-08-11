"""Repository for ``interview_sessions``.

Candidate-scoped reads and admin-scoped reads for evaluations.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.final_decision import FinalDecision
from app.models.interview import Interview
from app.models.interview_answer import InterviewAnswer
from app.models.interview_evaluation import InterviewEvaluation
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.repositories.base import BaseRepository


class InterviewSessionRepository(BaseRepository[InterviewSession]):
    model = InterviewSession

    async def get_owned_by_candidate(
        self,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> InterviewSession | None:
        """Load a session only if its interview belongs to ``candidate_id``.

        Eager-loads the parent interview (needed for JD/resume context inside
        the lifecycle service) and the session's questions with their answers
        (needed to render "session state" without a second round-trip). Returns
        ``None`` when the row is missing OR belongs to a different candidate,
        so callers can respond with a uniform 404 that never confirms whether
        another user's session exists.
        """
        stmt = (
            select(InterviewSession)
            .join(Interview, InterviewSession.interview_id == Interview.id)
            .where(
                InterviewSession.id == session_id,
                Interview.candidate_id == candidate_id,
            )
            .options(
                selectinload(InterviewSession.interview),
                selectinload(InterviewSession.questions).selectinload(
                    InterviewQuestion.answer
                ),
                selectinload(InterviewSession.evaluations),
                selectinload(InterviewSession.skill_scores),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_owned_for_update(
        self,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> InterviewSession | None:
        """Ownership-scoped session load with a transaction row lock.

        Answer advancement and submit claiming must be serialized so two
        concurrent retries cannot generate duplicate questions or schedule
        duplicate evaluations.
        """
        stmt = (
            select(InterviewSession)
            .join(Interview, InterviewSession.interview_id == Interview.id)
            .where(
                InterviewSession.id == session_id,
                Interview.candidate_id == candidate_id,
            )
            .options(
                selectinload(InterviewSession.interview),
                selectinload(InterviewSession.questions).selectinload(
                    InterviewQuestion.answer
                ),
                selectinload(InterviewSession.evaluations),
                selectinload(InterviewSession.skill_scores),
            )
            .with_for_update(of=InterviewSession)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def average_practice_final_score(
        self, candidate_id: uuid.UUID
    ) -> Decimal | None:
        """Average of FINAL ``overall_score`` for the candidate's practice sessions.

        Practice-only per the product decision: this powers the "Average Score"
        dashboard tile as a **learning-progress** signal, so assigned-interview
        AI scores (which feed the admin decision, not the candidate's growth)
        are deliberately excluded.
        """
        stmt = (
            select(func.avg(InterviewEvaluation.overall_score))
            .select_from(InterviewEvaluation)
            .join(
                InterviewSession,
                InterviewEvaluation.session_id == InterviewSession.id,
            )
            .join(Interview, InterviewSession.interview_id == Interview.id)
            .where(
                Interview.candidate_id == candidate_id,
                Interview.interview_type == "PRACTICE",
                InterviewEvaluation.evaluation_type == "FINAL",
                InterviewEvaluation.overall_score.is_not(None),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def latest_final_evaluation_for_interviews(
        self, interview_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, InterviewEvaluation]:
        """Return ``interview_id -> FINAL evaluation`` for the given interviews.

        Uses the latest session per interview (highest ``attempt_number``); the
        FINAL evaluation on that session is what "the result" of the interview
        refers to. Sessions without a FINAL row are omitted from the map so
        callers can distinguish "in review" from "evaluated".
        """
        if not interview_ids:
            return {}

        # Sessions with a FINAL evaluation, eager-loaded so the caller doesn't
        # trigger extra queries when rendering summaries.
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.interview_id.in_(interview_ids))
            .options(selectinload(InterviewSession.evaluations))
            .order_by(
                InterviewSession.interview_id,
                InterviewSession.attempt_number.desc(),
            )
        )
        result = await self.session.execute(stmt)

        latest_per_interview: dict[uuid.UUID, InterviewSession] = {}
        for session in result.scalars().all():
            latest_per_interview.setdefault(session.interview_id, session)

        finals: dict[uuid.UUID, InterviewEvaluation] = {}
        for interview_id, session in latest_per_interview.items():
            final = next(
                (
                    ev
                    for ev in session.evaluations
                    if ev.evaluation_type == "FINAL"
                ),
                None,
            )
            if final is not None:
                finals[interview_id] = final
        return finals

    async def question_counts_by_session(
        self, session_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, tuple[int, int]]:
        """Return ``session_id -> (total_questions, answered_questions)``.

        Counted with aggregates rather than walking
        ``session.questions`` so callers never risk a lazy load inside the
        async context, and so progress for a page of history costs two
        cheap COUNT queries instead of hydrating every question row.
        """
        if not session_ids:
            return {}

        total_stmt = (
            select(
                InterviewQuestion.session_id,
                func.count(InterviewQuestion.id),
            )
            .where(InterviewQuestion.session_id.in_(session_ids))
            .group_by(InterviewQuestion.session_id)
        )
        answered_stmt = (
            select(
                InterviewQuestion.session_id,
                func.count(InterviewAnswer.id),
            )
            .select_from(InterviewQuestion)
            .join(
                InterviewAnswer,
                InterviewAnswer.question_id == InterviewQuestion.id,
            )
            .where(
                InterviewQuestion.session_id.in_(session_ids),
                InterviewAnswer.is_submitted.is_(True),
            )
            .group_by(InterviewQuestion.session_id)
        )

        totals = {
            sid: count
            for sid, count in (await self.session.execute(total_stmt)).all()
        }
        answered = {
            sid: count
            for sid, count in (await self.session.execute(answered_stmt)).all()
        }
        return {
            sid: (totals.get(sid, 0), answered.get(sid, 0)) for sid in totals
        }

    async def latest_session_by_interview(
        self, interview_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, InterviewSession]:
        """Return the highest-attempt session for each interview id."""
        if not interview_ids:
            return {}
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.interview_id.in_(interview_ids))
            .options(selectinload(InterviewSession.final_decision))
            .order_by(
                InterviewSession.interview_id,
                InterviewSession.attempt_number.desc(),
            )
        )
        result = await self.session.execute(stmt)
        latest: dict[uuid.UUID, InterviewSession] = {}
        for session in result.scalars().all():
            latest.setdefault(session.interview_id, session)
        return latest

    # ------------------------------------------------------------------
    # Admin-scoped queries
    # ------------------------------------------------------------------

    _REVIEWABLE_STATUSES: tuple[str, ...] = (
        "EVALUATED",
        "COMPLETED",
    )

    _REVIEW_INTERVIEW_STATUSES: tuple[str, ...] = (
        "AI_EVALUATED",
        "ADMIN_REVIEW",
        "COMPLETED",
    )

    async def admin_count_pending_review(self) -> int:
        """Count sessions ready for admin evaluation (AI done, no admin decision yet)."""
        stmt = (
            select(func.count(InterviewSession.id))
            .select_from(InterviewSession)
            .join(Interview, InterviewSession.interview_id == Interview.id)
            .outerjoin(
                FinalDecision,
                FinalDecision.session_id == InterviewSession.id,
            )
            .where(
                Interview.interview_type == "ASSIGNED",
                Interview.status.in_(self._REVIEW_INTERVIEW_STATUSES),
                InterviewSession.status.in_(self._REVIEWABLE_STATUSES),
                FinalDecision.admin_decision.is_(None),
            )
        )
        return int((await self.session.execute(stmt)).scalar_one())

    async def admin_list_for_review(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Sequence[InterviewSession]:
        """Sessions awaiting admin review, with interview + candidate eager-loaded."""
        offset = (page - 1) * page_size
        stmt = (
            select(InterviewSession)
            .join(Interview, InterviewSession.interview_id == Interview.id)
            .outerjoin(
                FinalDecision,
                FinalDecision.session_id == InterviewSession.id,
            )
            .where(
                Interview.interview_type == "ASSIGNED",
                Interview.status.in_(self._REVIEW_INTERVIEW_STATUSES),
                InterviewSession.status.in_(self._REVIEWABLE_STATUSES),
            )
            .options(
                selectinload(InterviewSession.interview).selectinload(
                    Interview.candidate
                ),
                selectinload(InterviewSession.final_decision),
                selectinload(InterviewSession.evaluations),
            )
            .order_by(InterviewSession.ended_at.desc().nulls_last())
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(stmt)
        return result.scalars().unique().all()

    async def admin_get_evaluation_detail(
        self, session_id: uuid.UUID
    ) -> InterviewSession | None:
        """Full session with questions, answers, evaluations, and final decision."""
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .options(
                selectinload(InterviewSession.interview).selectinload(
                    Interview.candidate
                ),
                selectinload(InterviewSession.interview).selectinload(
                    Interview.assigned_by_user
                ),
                selectinload(InterviewSession.questions).selectinload(
                    InterviewQuestion.answer
                ),
                selectinload(InterviewSession.questions).selectinload(
                    InterviewQuestion.evaluations
                ),
                selectinload(InterviewSession.evaluations),
                selectinload(InterviewSession.final_decision).selectinload(
                    FinalDecision.decided_by_user
                ),
                selectinload(InterviewSession.skill_scores),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
