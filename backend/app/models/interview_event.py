"""``interview_events`` — append-only event log for an interview/session."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview import Interview
    from app.models.interview_session import InterviewSession
    from app.models.user import User

INTERVIEW_EVENT_TYPES = (
    "INTERVIEW_CREATED",
    "INTERVIEW_ASSIGNED",
    "INTERVIEW_SCHEDULED",
    "INTERVIEW_RESCHEDULED",
    "INTERVIEW_CANCELLED",
    "INTERVIEW_STARTED",
    "INTERVIEW_PAUSED",
    "INTERVIEW_RESUMED",
    "QUESTION_ASKED",
    "ANSWER_STARTED",
    "ANSWER_SUBMITTED",
    "CODING_SUBMISSION",
    "INTERVIEW_SUBMITTED",
    "AI_EVALUATION_STARTED",
    "AI_EVALUATION_COMPLETED",
    "ADMIN_REVIEW_STARTED",
    "ADMIN_DECISION_MADE",
    "RESULT_PUBLISHED",
    "INTERVIEW_EXPIRED",
)


class InterviewEvent(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "interview_events"

    interview_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interviews.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    meta: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    interview: Mapped[Interview] = relationship(back_populates="events")
    session: Mapped[InterviewSession | None] = relationship(back_populates="events")
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_user_id])

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('INTERVIEW_CREATED', 'INTERVIEW_ASSIGNED', "
            "'INTERVIEW_SCHEDULED', 'INTERVIEW_RESCHEDULED', 'INTERVIEW_CANCELLED', "
            "'INTERVIEW_STARTED', 'INTERVIEW_PAUSED', 'INTERVIEW_RESUMED', "
            "'QUESTION_ASKED', 'ANSWER_STARTED', 'ANSWER_SUBMITTED', "
            "'CODING_SUBMISSION', 'INTERVIEW_SUBMITTED', 'AI_EVALUATION_STARTED', "
            "'AI_EVALUATION_COMPLETED', 'ADMIN_REVIEW_STARTED', 'ADMIN_DECISION_MADE', "
            "'RESULT_PUBLISHED', 'INTERVIEW_EXPIRED')",
            name="chk_interview_event_type",
        ),
        Index("idx_interview_events_actor", "actor_user_id"),
        Index("idx_interview_events_created_at", text("created_at DESC")),
        Index("idx_interview_events_interview", "interview_id", "created_at"),
        Index("idx_interview_events_session", "session_id", "created_at"),
        Index("idx_interview_events_type", "event_type"),
    )
