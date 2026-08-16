"""``email_verifications`` — hashed registration OTPs (never plaintext)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class EmailVerification(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "email_verifications"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint("expires_at > created_at", name="expiry"),
        Index("idx_email_verifications_email_lower", text("lower(email)")),
        Index("idx_email_verifications_created_at", "created_at"),
        Index(
            "idx_email_verifications_active",
            text("lower(email)"),
            "created_at",
            postgresql_where=text("verified_at IS NULL AND consumed_at IS NULL"),
        ),
    )
