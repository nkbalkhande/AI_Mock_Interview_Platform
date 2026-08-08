"""``resumes`` — one resume per user, pointing at versioned files."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.resume_version import ResumeVersion
    from app.models.user import User


class Resume(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resumes"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )

    user: Mapped[User] = relationship(back_populates="resume")
    versions: Mapped[list[ResumeVersion]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_resumes_user_id"),
        CheckConstraint("current_version_number >= 1", name="chk_resumes_version"),
    )
