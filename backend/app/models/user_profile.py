"""``user_profiles`` — extended candidate profile (1:1 with users)."""

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserProfile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    current_organization: Mapped[str | None] = mapped_column(String(200), nullable=True)
    current_designation: Mapped[str | None] = mapped_column(String(150), nullable=True)
    years_of_experience: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    profile_photo_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(30), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship(back_populates="profile")

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_profiles_user_id"),
        CheckConstraint(
            "years_of_experience IS NULL OR years_of_experience >= 0",
            name="chk_user_profiles_experience",
        ),
        Index("idx_user_profiles_organization", "current_organization"),
    )
