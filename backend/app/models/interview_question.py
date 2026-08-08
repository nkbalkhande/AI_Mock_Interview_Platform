"""``interview_questions`` — questions asked within a session."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.coding_submission import CodingSubmission
    from app.models.interview_answer import InterviewAnswer
    from app.models.interview_evaluation import InterviewEvaluation
    from app.models.interview_session import InterviewSession

QUESTION_TYPES = (
    "TECHNICAL",
    "PROJECT",
    "BEHAVIORAL",
    "CODING",
    "SYSTEM_DESIGN",
    "FOLLOW_UP",
)
QUESTION_DIFFICULTIES = ("EASY", "MEDIUM", "HARD")
QUESTION_SOURCES = ("AI_GENERATED", "INTERVIEWER_CREATED", "QUESTION_BANK")


class InterviewQuestion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_questions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_number: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[str | None] = mapped_column(String(20), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(150), nullable=True)
    skill: Mapped[str | None] = mapped_column(String(150), nullable=True)
    source: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'AI_GENERATED'")
    )
    expected_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    question_metadata: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    session: Mapped[InterviewSession] = relationship(back_populates="questions")
    answer: Mapped[InterviewAnswer | None] = relationship(
        back_populates="question", uselist=False, cascade="all, delete-orphan"
    )
    coding_submissions: Mapped[list[CodingSubmission]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list[InterviewEvaluation]] = relationship(
        back_populates="question"
    )

    __table_args__ = (
        UniqueConstraint("session_id", "question_number", name="uq_question_number"),
        CheckConstraint("question_number >= 1", name="chk_question_number"),
        CheckConstraint(
            "question_type IN ('TECHNICAL', 'PROJECT', 'BEHAVIORAL', 'CODING', "
            "'SYSTEM_DESIGN', 'FOLLOW_UP')",
            name="chk_question_type",
        ),
        CheckConstraint(
            "difficulty IS NULL OR difficulty IN ('EASY', 'MEDIUM', 'HARD')",
            name="chk_question_difficulty",
        ),
        CheckConstraint(
            "source IN ('AI_GENERATED', 'INTERVIEWER_CREATED', 'QUESTION_BANK')",
            name="chk_question_source",
        ),
        Index("idx_interview_questions_session", "session_id"),
        Index("idx_interview_questions_skill", "skill"),
        Index("idx_interview_questions_type", "question_type"),
    )
