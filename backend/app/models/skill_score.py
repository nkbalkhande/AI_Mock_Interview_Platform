"""``skill_scores`` — per-skill scores derived for a session."""

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
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview_session import InterviewSession


class SkillScore(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "skill_scores"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(String(150), nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default=text("10")
    )
    strength: Mapped[str | None] = mapped_column(Text, nullable=True)
    improvement_area: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )

    session: Mapped[InterviewSession] = relationship(back_populates="skill_scores")

    __table_args__ = (
        UniqueConstraint("session_id", "skill_name", name="uq_skill_score"),
        CheckConstraint("score >= 0 AND score <= max_score", name="chk_skill_score"),
        CheckConstraint("max_score > 0", name="chk_skill_max_score"),
        Index("idx_skill_scores_session", "session_id"),
        Index("idx_skill_scores_skill", "skill_name"),
    )
