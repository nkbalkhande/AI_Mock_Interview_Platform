"""``job_roles`` — catalog of roles interviews can target."""

from __future__ import annotations

from typing import TYPE_CHECKING

from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.interview import Interview


class JobRole(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "job_roles"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    experience_min: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    experience_max: Mapped[Decimal | None] = mapped_column(
        Numeric(4, 2), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )

    interviews: Mapped[list[Interview]] = relationship(
        back_populates="job_role", foreign_keys="Interview.job_role_id"
    )

    @validates("requirements")
    def validate_requirements(self, _: str, value: object) -> list[str]:
        return _validate_string_array(value, max_items=20, max_length=300)

    @validates("skills")
    def validate_skills(self, _: str, value: object) -> list[str]:
        return _validate_string_array(value, max_items=30, max_length=100)

    __table_args__ = (
        UniqueConstraint("name", name="uq_job_roles_name"),
        CheckConstraint(
            "(experience_min IS NULL OR experience_min >= 0) AND "
            "(experience_max IS NULL OR experience_max >= 0) AND "
            "(experience_min IS NULL OR experience_max IS NULL OR "
            "experience_max >= experience_min)",
            name="chk_job_role_experience",
        ),
        CheckConstraint(
            "jsonb_typeof(requirements) = 'array' "
            "AND jsonb_array_length(requirements) <= 20",
            name="chk_job_role_requirements_shape",
        ),
        CheckConstraint(
            "jsonb_typeof(skills) = 'array' "
            "AND jsonb_array_length(skills) <= 30",
            name="chk_job_role_skills_shape",
        ),
        Index("idx_job_roles_active", "is_active"),
    )


def _validate_string_array(
    value: object, *, max_items: int, max_length: int
) -> list[str]:
    if not isinstance(value, list) or len(value) > max_items:
        raise ValueError("Value must be a bounded JSON array.")
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError("Every array item must be a string.")
        cleaned = item.strip()
        if not cleaned or len(cleaned) > max_length:
            raise ValueError("Array items must be non-empty and within length limits.")
        normalized.append(cleaned)
    return normalized
