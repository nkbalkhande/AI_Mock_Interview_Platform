"""Repository for ``coding_submissions``.

MVP scope: submissions are stored as-code only — no sandboxed execution. The
LLM evaluator reviews the code text; ``execution_status`` / ``test_cases_*`` /
timing columns stay at their defaults until a real runner is wired up.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select

from app.models.coding_submission import CodingSubmission
from app.repositories.base import BaseRepository


class CodingSubmissionRepository(BaseRepository[CodingSubmission]):
    model = CodingSubmission

    async def list_by_question(
        self, question_id: uuid.UUID
    ) -> Sequence[CodingSubmission]:
        stmt = (
            select(CodingSubmission)
            .where(CodingSubmission.question_id == question_id)
            .order_by(CodingSubmission.submitted_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_final(
        self, question_id: uuid.UUID
    ) -> CodingSubmission | None:
        """Return the final submission for a question, if one exists."""
        stmt = select(CodingSubmission).where(
            CodingSubmission.question_id == question_id,
            CodingSubmission.is_final_submission.is_(True),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()
