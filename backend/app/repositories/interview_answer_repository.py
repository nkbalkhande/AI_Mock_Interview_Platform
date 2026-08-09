"""Repository for ``interview_answers``.

There is exactly one answer row per question (DB unique constraint), so this
repo exposes upsert semantics: if the candidate re-submits the same question
(e.g. after a refresh) we mutate the existing row rather than raise a conflict.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.interview_answer import InterviewAnswer
from app.repositories.base import BaseRepository


class InterviewAnswerRepository(BaseRepository[InterviewAnswer]):
    model = InterviewAnswer

    async def get_by_question(
        self, question_id: uuid.UUID
    ) -> InterviewAnswer | None:
        stmt = select(InterviewAnswer).where(
            InterviewAnswer.question_id == question_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
