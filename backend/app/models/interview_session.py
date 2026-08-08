"""``interview_sessions`` — a single attempt at an interview."""

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.final_decision import FinalDecision
    from app.models.interview import Interview
    from app.models.interview_evaluation import InterviewEvaluation
    from app.models.interview_event import InterviewEvent
    from app.models.interview_question import InterviewQuestion
    from app.models.skill_score import SkillScore

SESSION_STATUSES = (
    "NOT_STARTED",
    "IN_PROGRESS",
    "PAUSED",
    "SUBMITTED",
    "EVALUATING",
    "EVALUATED",
    "COMPLETED",
    "ABANDONED",
)


class InterviewSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interview_sessions"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_question_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'NOT_STARTED'")
    )
    interview_state: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    interview: Mapped[Interview] = relationship(back_populates="sessions")
    questions: Mapped[list[InterviewQuestion]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list[InterviewEvaluation]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    skill_scores: Mapped[list[SkillScore]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    final_decision: Mapped[FinalDecision | None] = relationship(
        back_populates="session", uselist=False, cascade="all, delete-orphan"
    )
    events: Mapped[list[InterviewEvent]] = relationship(back_populates="session")

    __table_args__ = (
        UniqueConstraint(
            "interview_id", "attempt_number", name="uq_interview_attempt"
        ),
        CheckConstraint("attempt_number >= 1", name="chk_attempt_number"),
        CheckConstraint(
            "current_question_number >= 0", name="chk_session_question_number"
        ),
        CheckConstraint(
            "status IN ('NOT_STARTED', 'IN_PROGRESS', 'PAUSED', 'SUBMITTED', "
            "'EVALUATING', 'EVALUATED', 'COMPLETED', 'ABANDONED')",
            name="chk_session_status",
        ),
        CheckConstraint(
            "ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at",
            name="chk_session_time",
        ),
        Index("idx_interview_sessions_interview_id", "interview_id"),
        Index("idx_interview_sessions_status", "status"),
    )
