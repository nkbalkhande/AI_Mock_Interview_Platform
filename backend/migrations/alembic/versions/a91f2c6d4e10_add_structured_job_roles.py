"""add structured job roles

Revision ID: a91f2c6d4e10
Revises: d8c718064db2
Create Date: 2026-08-09 18:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a91f2c6d4e10"
down_revision: Union[str, None] = "d8c718064db2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_roles",
        sa.Column(
            "requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "job_roles",
        sa.Column(
            "skills",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "job_roles",
        sa.Column("experience_min", sa.Numeric(precision=4, scale=2), nullable=True),
    )
    op.add_column(
        "job_roles",
        sa.Column("experience_max", sa.Numeric(precision=4, scale=2), nullable=True),
    )
    op.create_check_constraint(
        "chk_job_role_experience",
        "job_roles",
        "(experience_min IS NULL OR experience_min >= 0) AND "
        "(experience_max IS NULL OR experience_max >= 0) AND "
        "(experience_min IS NULL OR experience_max IS NULL OR "
        "experience_max >= experience_min)",
    )
    op.create_check_constraint(
        "chk_job_role_requirements_shape",
        "job_roles",
        "jsonb_typeof(requirements) = 'array' "
        "AND jsonb_array_length(requirements) <= 20",
    )
    op.create_check_constraint(
        "chk_job_role_skills_shape",
        "job_roles",
        "jsonb_typeof(skills) = 'array' "
        "AND jsonb_array_length(skills) <= 30",
    )
    op.execute(
        sa.text(
            """
            WITH seed (
                id, name, description, requirements, skills,
                experience_min, experience_max
            ) AS (
              VALUES
              ('10000000-0000-4000-8000-000000000001'::uuid, 'AI Engineer',
               'Build, deploy, and operate production AI systems.',
               '["Production AI delivery", "Model integration", "Reliable APIs"]'::jsonb,
               '["Python", "Machine Learning", "MLOps", "Cloud"]'::jsonb, 2, 8),
              ('10000000-0000-4000-8000-000000000002'::uuid, 'GenAI Engineer',
               'Design and productionize generative AI applications.',
               '["LLM application design", "Retrieval pipelines", "Evaluation and guardrails"]'::jsonb,
               '["Python", "LLMs", "RAG", "Prompt Engineering"]'::jsonb, 2, 8),
              ('10000000-0000-4000-8000-000000000003'::uuid, 'ML Engineer',
               'Develop scalable machine-learning training and serving systems.',
               '["ML pipelines", "Model serving", "Monitoring"]'::jsonb,
               '["Python", "Machine Learning", "MLOps", "Data Pipelines"]'::jsonb, 2, 8),
              ('10000000-0000-4000-8000-000000000004'::uuid, 'Data Scientist',
               'Use statistics and machine learning to solve business problems.',
               '["Experiment design", "Predictive modeling", "Business communication"]'::jsonb,
               '["Python", "Statistics", "Machine Learning", "SQL"]'::jsonb, 1, 8),
              ('10000000-0000-4000-8000-000000000005'::uuid, 'Data Analyst',
               'Turn data into trustworthy business insights.',
               '["Data analysis", "Dashboarding", "Stakeholder communication"]'::jsonb,
               '["SQL", "Spreadsheets", "BI Tools", "Statistics"]'::jsonb, 0, 6),
              ('10000000-0000-4000-8000-000000000006'::uuid, 'Backend Engineer',
               'Build reliable APIs and distributed backend services.',
               '["API design", "Data modeling", "Scalable services"]'::jsonb,
               '["Python", "SQL", "System Design", "Cloud"]'::jsonb, 1, 8)
            )
            INSERT INTO job_roles (
                id, name, description, requirements, skills,
                experience_min, experience_max, is_active,
                created_at, updated_at
            )
            SELECT
                seed.id, seed.name, seed.description, seed.requirements,
                seed.skills, seed.experience_min, seed.experience_max, true,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM seed
            WHERE NOT EXISTS (
                SELECT 1
                FROM job_roles AS existing
                WHERE existing.id = seed.id OR existing.name = seed.name
            )
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH owned (id, name) AS (
                VALUES
                ('10000000-0000-4000-8000-000000000001'::uuid, 'AI Engineer'),
                ('10000000-0000-4000-8000-000000000002'::uuid, 'GenAI Engineer'),
                ('10000000-0000-4000-8000-000000000003'::uuid, 'ML Engineer'),
                ('10000000-0000-4000-8000-000000000004'::uuid, 'Data Scientist'),
                ('10000000-0000-4000-8000-000000000005'::uuid, 'Data Analyst'),
                ('10000000-0000-4000-8000-000000000006'::uuid, 'Backend Engineer')
            )
            DELETE FROM job_roles
            USING owned
            WHERE job_roles.id = owned.id
              AND job_roles.name = owned.name
            """
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE job_roles DROP CONSTRAINT IF EXISTS "
            "ck_job_roles_chk_job_role_skills_shape"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE job_roles DROP CONSTRAINT IF EXISTS "
            "ck_job_roles_chk_job_role_requirements_shape"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE job_roles DROP CONSTRAINT IF EXISTS "
            "ck_job_roles_chk_job_role_experience"
        )
    )
    op.drop_column("job_roles", "experience_max")
    op.drop_column("job_roles", "experience_min")
    op.drop_column("job_roles", "skills")
    op.drop_column("job_roles", "requirements")
