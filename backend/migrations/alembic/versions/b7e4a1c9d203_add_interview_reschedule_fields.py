"""add interview reschedule fields and RESCHEDULED status

Revision ID: b7e4a1c9d203
Revises: a91f2c6d4e10
Create Date: 2026-08-14 10:10:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7e4a1c9d203"
down_revision: Union[str, None] = "a91f2c6d4e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "interviews",
        sa.Column("original_scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "interviews",
        sa.Column("rescheduled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "interviews",
        sa.Column(
            "reschedule_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
    )
    op.add_column(
        "interviews",
        sa.Column("reschedule_reason", sa.Text(), nullable=True),
    )
    op.add_column(
        "interviews",
        sa.Column("rescheduled_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_interviews_rescheduled_by_users"),
        "interviews",
        "users",
        ["rescheduled_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.execute("ALTER TABLE interviews DROP CONSTRAINT chk_interview_status")
    op.execute(
        "ALTER TABLE interviews ADD CONSTRAINT chk_interview_status "
        "CHECK (status IN ('DRAFT', 'ASSIGNED', 'SCHEDULED', 'AVAILABLE', "
        "'IN_PROGRESS', 'SUBMITTED', 'AI_EVALUATED', 'ADMIN_REVIEW', "
        "'COMPLETED', 'CANCELLED', 'EXPIRED', 'RESCHEDULED'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE interviews DROP CONSTRAINT chk_interview_status")
    op.execute(
        "ALTER TABLE interviews ADD CONSTRAINT chk_interview_status "
        "CHECK (status IN ('DRAFT', 'ASSIGNED', 'SCHEDULED', 'AVAILABLE', "
        "'IN_PROGRESS', 'SUBMITTED', 'AI_EVALUATED', 'ADMIN_REVIEW', "
        "'COMPLETED', 'CANCELLED', 'EXPIRED'))"
    )
    op.drop_constraint(
        op.f("fk_interviews_rescheduled_by_users"), "interviews", type_="foreignkey"
    )
    op.drop_column("interviews", "rescheduled_by")
    op.drop_column("interviews", "reschedule_reason")
    op.drop_column("interviews", "reschedule_count")
    op.drop_column("interviews", "rescheduled_at")
    op.drop_column("interviews", "original_scheduled_at")
