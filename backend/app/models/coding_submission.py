"""``coding_submissions`` — code runs for CODING questions."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview_answer import InterviewAnswer
    from app.models.interview_question import InterviewQuestion

EXECUTION_STATUSES = (
    "PENDING",
    "RUNNING",
    "PASSED",
    "FAILED",
    "TIMEOUT",
    "MEMORY_LIMIT",
    "RUNTIME_ERROR",
    "COMPILE_ERROR",
)


class CodingSubmission(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "coding_submissions"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_answers.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    execution_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    test_cases_passed: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    test_cases_total: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    execution_time_ms: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    memory_used_mb: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3), nullable=True
    )
    is_final_submission: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    execution_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    meta: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    question: Mapped[InterviewQuestion] = relationship(
        back_populates="coding_submissions"
    )
    answer: Mapped[InterviewAnswer | None] = relationship(
        back_populates="coding_submissions"
    )

    __table_args__ = (
        CheckConstraint(
            "test_cases_passed >= 0 AND test_cases_total >= 0 "
            "AND test_cases_passed <= test_cases_total",
            name="chk_coding_test_cases",
        ),
        CheckConstraint(
            "execution_time_ms IS NULL OR execution_time_ms >= 0",
            name="chk_coding_execution_time",
        ),
        CheckConstraint(
            "memory_used_mb IS NULL OR memory_used_mb >= 0",
            name="chk_coding_memory",
        ),
        CheckConstraint(
            "execution_status IS NULL OR execution_status IN ('PENDING', 'RUNNING', "
            "'PASSED', 'FAILED', 'TIMEOUT', 'MEMORY_LIMIT', 'RUNTIME_ERROR', "
            "'COMPILE_ERROR')",
            name="chk_coding_execution_status",
        ),
        Index("idx_coding_submissions_question", "question_id"),
        Index("idx_coding_submissions_answer", "answer_id"),
        Index("idx_coding_submissions_submitted_at", "submitted_at"),
        Index(
            "uq_coding_final_submission",
            "question_id",
            unique=True,
            postgresql_where=text("is_final_submission = true"),
        ),
    )
