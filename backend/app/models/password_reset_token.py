"""``password_reset_tokens`` — one-time password reset tokens (hashed)."""

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
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class PasswordResetToken(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="password_reset_tokens")

    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_password_reset_token_hash"),
        CheckConstraint(
            "expires_at > created_at", name="chk_password_reset_token_expiry"
        ),
        CheckConstraint(
            "used_at IS NULL OR used_at >= created_at",
            name="chk_password_reset_token_used",
        ),
        Index("idx_password_reset_tokens_user_id", "user_id"),
        Index("idx_password_reset_tokens_expires_at", "expires_at"),
        Index(
            "idx_password_reset_tokens_active",
            "user_id",
            "expires_at",
            postgresql_where=text("used_at IS NULL"),
        ),
    )
