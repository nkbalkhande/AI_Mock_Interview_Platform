"""``resume_versions`` — versioned uploaded resume files + extracted text."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
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
    from app.models.resume import Resume


class ResumeVersion(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "resume_versions"

    resume_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("resumes.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    meta: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    resume: Mapped[Resume] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_version"),
        CheckConstraint("version_number >= 1", name="chk_resume_version_number"),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0",
            name="chk_resume_file_size",
        ),
        Index("idx_resume_versions_resume_id", "resume_id"),
        Index("idx_resume_versions_current", "resume_id", "is_current"),
        Index(
            "uq_one_current_resume_version",
            "resume_id",
            unique=True,
            postgresql_where=text("is_current = true"),
        ),
    )
