"""Repository for ``interview_evaluations``.

Only FINAL rows are written by this task's evaluator; per-question evaluations
are not yet in scope. A DB unique index enforces one FINAL row per session, so
callers that retry the evaluator must first check whether one exists.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.interview_evaluation import InterviewEvaluation
from app.repositories.base import BaseRepository


class InterviewEvaluationRepository(BaseRepository[InterviewEvaluation]):
    model = InterviewEvaluation

    async def get_final(
        self, session_id: uuid.UUID
    ) -> InterviewEvaluation | None:
        stmt = select(InterviewEvaluation).where(
            InterviewEvaluation.session_id == session_id,
            InterviewEvaluation.evaluation_type == "FINAL",
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
