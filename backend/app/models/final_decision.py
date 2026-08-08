"""``final_decisions`` — AI verdict + admin decision for a session (1:1)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession
    from app.models.user import User

FINAL_AI_VERDICTS = ("CLEARED", "NOT_CLEARED", "BORDERLINE", "NEEDS_REVIEW")
ADMIN_DECISIONS = ("CLEARED", "NOT_CLEARED", "NEEDS_FURTHER_REVIEW")


class FinalDecision(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "final_decisions"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    ai_verdict: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ai_overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_strengths: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    ai_weaknesses: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    ai_improvement_areas: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    admin_decision: Mapped[str | None] = mapped_column(String(30), nullable=True)
    admin_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result_published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    session: Mapped[InterviewSession] = relationship(back_populates="final_decision")
    decided_by_user: Mapped[User | None] = relationship(foreign_keys=[decided_by])

    __table_args__ = (
        UniqueConstraint("session_id", name="uq_final_decision_session"),
        CheckConstraint(
            "ai_verdict IS NULL OR ai_verdict IN ('CLEARED', 'NOT_CLEARED', "
            "'BORDERLINE', 'NEEDS_REVIEW')",
            name="chk_final_ai_verdict",
        ),
        CheckConstraint(
            "ai_overall_score IS NULL OR (ai_overall_score >= 0 "
            "AND ai_overall_score <= 10)",
            name="chk_final_ai_score",
        ),
        CheckConstraint(
            "admin_decision IS NULL OR admin_decision IN ('CLEARED', 'NOT_CLEARED', "
            "'NEEDS_FURTHER_REVIEW')",
            name="chk_admin_decision",
        ),
        Index("idx_final_decisions_session", "session_id"),
        Index("idx_final_decisions_decided_by", "decided_by"),
        Index("idx_final_decisions_admin_decision", "admin_decision"),
    )
