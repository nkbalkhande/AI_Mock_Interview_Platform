"""``interview_answers`` — a candidate's answer to a question (1:1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.coding_submission import CodingSubmission
    from app.models.interview_question import InterviewQuestion


class InterviewAnswer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_answers"

    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    response_time_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_submitted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    answer_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    question: Mapped[InterviewQuestion] = relationship(back_populates="answer")
    coding_submissions: Mapped[list[CodingSubmission]] = relationship(
        back_populates="answer"
    )

    __table_args__ = (
        UniqueConstraint("question_id", name="uq_interview_answer_question"),
        CheckConstraint(
            "response_time_seconds IS NULL OR response_time_seconds >= 0",
            name="chk_answer_response_time",
        ),
        Index("idx_interview_answers_submitted", "is_submitted"),
    )
