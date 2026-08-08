"""``interview_evaluations`` — per-question and final AI evaluations."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview_question import InterviewQuestion
    from app.models.interview_session import InterviewSession

EVALUATION_TYPES = ("QUESTION", "FINAL")
AI_VERDICTS = ("CLEARED", "NOT_CLEARED", "BORDERLINE", "NEEDS_REVIEW")


class InterviewEvaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_evaluations"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=True,
    )
    evaluation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    correctness_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    technical_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    communication_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    reasoning_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    ai_verdict: Mapped[str | None] = mapped_column(String(30), nullable=True)
    confidence: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    strengths: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    weaknesses: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    improvement_areas: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    model_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(100), nullable=True)
    evaluation_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    session: Mapped[InterviewSession] = relationship(back_populates="evaluations")
    question: Mapped[InterviewQuestion | None] = relationship(
        back_populates="evaluations"
    )

    __table_args__ = (
        CheckConstraint(
            "evaluation_type IN ('QUESTION', 'FINAL')", name="chk_evaluation_type"
        ),
        CheckConstraint(
            "(correctness_score IS NULL OR (correctness_score >= 0 "
            "AND correctness_score <= 10)) "
            "AND (technical_score IS NULL OR (technical_score >= 0 "
            "AND technical_score <= 10)) "
            "AND (communication_score IS NULL OR (communication_score >= 0 "
            "AND communication_score <= 10)) "
            "AND (reasoning_score IS NULL OR (reasoning_score >= 0 "
            "AND reasoning_score <= 10)) "
            "AND (overall_score IS NULL OR (overall_score >= 0 "
            "AND overall_score <= 10))",
            name="chk_evaluation_scores",
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="chk_evaluation_confidence",
        ),
        CheckConstraint(
            "ai_verdict IS NULL OR ai_verdict IN ('CLEARED', 'NOT_CLEARED', "
            "'BORDERLINE', 'NEEDS_REVIEW')",
            name="chk_evaluation_verdict",
        ),
        CheckConstraint(
            "(evaluation_type = 'QUESTION' AND question_id IS NOT NULL) "
            "OR (evaluation_type = 'FINAL' AND question_id IS NULL)",
            name="chk_evaluation_question_scope",
        ),
        Index("idx_interview_evaluations_session", "session_id"),
        Index("idx_interview_evaluations_question", "question_id"),
        Index("idx_interview_evaluations_type", "evaluation_type"),
        Index(
            "uq_final_evaluation",
            "session_id",
            unique=True,
            postgresql_where=text("evaluation_type = 'FINAL'"),
        ),
        Index(
            "uq_question_evaluation",
            "session_id",
            "question_id",
            unique=True,
            postgresql_where=text("evaluation_type = 'QUESTION'"),
        ),
    )
