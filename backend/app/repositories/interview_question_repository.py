"""Repository for ``interview_questions``.

Owns write access to questions plus the read paths the lifecycle service needs
to reconstruct a session (list all past questions, find the "current" one, etc.).
Ordering is always by ``question_number`` — the DB has a unique constraint on
``(session_id, question_number)`` so numbers are the source of truth, not
``created_at``.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.interview_question import InterviewQuestion
from app.repositories.base import BaseRepository


class InterviewQuestionRepository(BaseRepository[InterviewQuestion]):
    model = InterviewQuestion

    async def list_by_session(
        self,
        session_id: uuid.UUID,
        *,
        with_answer: bool = False,
    ) -> Sequence[InterviewQuestion]:
        """All questions for a session, oldest first."""
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_id)
            .order_by(InterviewQuestion.question_number.asc())
        )
        if with_answer:
            stmt = stmt.options(selectinload(InterviewQuestion.answer))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_number(
        self, session_id: uuid.UUID, question_number: int
    ) -> InterviewQuestion | None:
        stmt = (
            select(InterviewQuestion)
            .where(
                InterviewQuestion.session_id == session_id,
                InterviewQuestion.question_number == question_number,
            )
            .options(selectinload(InterviewQuestion.answer))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_latest_for_session(
        self, session_id: uuid.UUID
    ) -> InterviewQuestion | None:
        """Highest-numbered question in the session — treat as "current"."""
        stmt = (
            select(InterviewQuestion)
            .where(InterviewQuestion.session_id == session_id)
            .options(selectinload(InterviewQuestion.answer))
            .order_by(InterviewQuestion.question_number.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
