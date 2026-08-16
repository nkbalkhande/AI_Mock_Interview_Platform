"""add email_verifications table and users.email_verified_at

Revision ID: c3f8e2a1b904
Revises: b7e4a1c9d203
Create Date: 2026-08-15 23:20:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3f8e2a1b904"
down_revision: Union[str, None] = "b7e4a1c9d203"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "email_verifications",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("otp_hash", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.CheckConstraint(
            "attempts >= 0",
            name=op.f("ck_email_verifications_attempts_non_negative"),
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name=op.f("ck_email_verifications_expiry"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_email_verifications")),
    )
    op.create_index(
        "idx_email_verifications_email_lower",
        "email_verifications",
        [sa.text("lower(email)")],
        unique=False,
    )
    op.create_index(
        "idx_email_verifications_created_at",
        "email_verifications",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "idx_email_verifications_active",
        "email_verifications",
        [sa.text("lower(email)"), "created_at"],
        unique=False,
        postgresql_where=sa.text("verified_at IS NULL AND consumed_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("idx_email_verifications_active", table_name="email_verifications")
    op.drop_index(
        "idx_email_verifications_created_at", table_name="email_verifications"
    )
    op.drop_index(
        "idx_email_verifications_email_lower", table_name="email_verifications"
    )
    op.drop_table("email_verifications")
    op.drop_column("users", "email_verified_at")
