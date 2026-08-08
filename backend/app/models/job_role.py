"""``job_roles`` — catalog of roles interviews can target."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview import Interview


class JobRole(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job_roles"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    interviews: Mapped[list[Interview]] = relationship(
        back_populates="job_role", foreign_keys="Interview.job_role_id"
    )

    __table_args__ = (
        UniqueConstraint("name", name="uq_job_roles_name"),
        Index("idx_job_roles_active", "is_active"),
    )
