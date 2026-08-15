"""``interviews`` — a scheduled/practice interview for a candidate.

``interview_type`` is either PRACTICE (self-serve, requires ``practice_type``) or
ASSIGNED (created by an admin, ``practice_type`` must be NULL). Role/JD details are
snapshotted so historical interviews are stable even if the source role changes.
"""

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
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview_event import InterviewEvent
    from app.models.interview_session import InterviewSession
    from app.models.job_role import JobRole
    from app.models.resume_version import ResumeVersion
    from app.models.user import User

INTERVIEW_TYPES = ("PRACTICE", "ASSIGNED")
PRACTICE_TYPES = ("JD_BASED", "ROLE_BASED")
INTERVIEW_STATUSES = (
    "DRAFT",
    "ASSIGNED",
    "SCHEDULED",
    "AVAILABLE",
    "IN_PROGRESS",
    "SUBMITTED",
    "AI_EVALUATED",
    "ADMIN_REVIEW",
    "COMPLETED",
    "CANCELLED",
    "EXPIRED",
    "RESCHEDULED",
)


class Interview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "interviews"

    candidate_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    job_role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_roles.id", ondelete="SET NULL"),
        nullable=True,
    )
    resume_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    interview_type: Mapped[str] = mapped_column(String(30), nullable=False)
    practice_type: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role_name_snapshot: Mapped[str | None] = mapped_column(String(150), nullable=True)
    job_description_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_requirements_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_experience_min: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    required_experience_max: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    timezone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("30")
    )
    access_start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    access_end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, server_default=text("'DRAFT'")
    )
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rescheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reschedule_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    reschedule_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rescheduled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    candidate: Mapped[User] = relationship(foreign_keys=[candidate_id])
    assigned_by_user: Mapped[User | None] = relationship(foreign_keys=[assigned_by])
    rescheduled_by_user: Mapped[User | None] = relationship(
        foreign_keys=[rescheduled_by]
    )
    job_role: Mapped[JobRole | None] = relationship(
        back_populates="interviews", foreign_keys=[job_role_id]
    )
    resume_version: Mapped[ResumeVersion | None] = relationship(
        foreign_keys=[resume_version_id]
    )
    sessions: Mapped[list[InterviewSession]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )
    events: Mapped[list[InterviewEvent]] = relationship(
        back_populates="interview", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "interview_type IN ('PRACTICE', 'ASSIGNED')", name="chk_interview_type"
        ),
        CheckConstraint(
            "practice_type IS NULL OR practice_type IN ('JD_BASED', 'ROLE_BASED')",
            name="chk_practice_type",
        ),
        CheckConstraint(
            "(interview_type = 'PRACTICE' AND practice_type IS NOT NULL) "
            "OR (interview_type = 'ASSIGNED' AND practice_type IS NULL)",
            name="chk_practice_configuration",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ASSIGNED', 'SCHEDULED', 'AVAILABLE', 'IN_PROGRESS', "
            "'SUBMITTED', 'AI_EVALUATED', 'ADMIN_REVIEW', 'COMPLETED', 'CANCELLED', "
            "'EXPIRED', 'RESCHEDULED')",
            name="chk_interview_status",
        ),
        CheckConstraint(
            "duration_minutes > 0 AND duration_minutes <= 180",
            name="chk_interview_duration",
        ),
        CheckConstraint(
            "(required_experience_min IS NULL OR required_experience_min >= 0) "
            "AND (required_experience_max IS NULL OR required_experience_max >= 0) "
            "AND (required_experience_min IS NULL OR required_experience_max IS NULL "
            "OR required_experience_max >= required_experience_min)",
            name="chk_interview_experience",
        ),
        CheckConstraint(
            "access_start_at IS NULL OR access_end_at IS NULL "
            "OR access_end_at > access_start_at",
            name="chk_interview_access_window",
        ),
        Index("idx_interviews_candidate", "candidate_id"),
        Index("idx_interviews_assigned_by", "assigned_by"),
        Index("idx_interviews_job_role", "job_role_id"),
        Index("idx_interviews_resume_version", "resume_version_id"),
        Index("idx_interviews_scheduled_at", "scheduled_at"),
        Index("idx_interviews_status", "status"),
    )
