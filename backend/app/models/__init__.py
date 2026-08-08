"""ORM models package.

Importing this package registers every model on ``Base.metadata`` so Alembic
autogenerate and SQLAlchemy relationship resolution see all 20 tables.
"""

from __future__ import annotations

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.audit_log import AuditLog
from app.models.coding_submission import CodingSubmission
from app.models.final_decision import FinalDecision
from app.models.interview import Interview
from app.models.interview_answer import InterviewAnswer
from app.models.interview_evaluation import InterviewEvaluation
from app.models.interview_event import InterviewEvent
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.job_role import JobRole
from app.models.notification import Notification
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.role import Role
from app.models.skill_score import SkillScore
from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_role import UserRole

__all__ = [
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "AuditLog",
    "CodingSubmission",
    "FinalDecision",
    "Interview",
    "InterviewAnswer",
    "InterviewEvaluation",
    "InterviewEvent",
    "InterviewQuestion",
    "InterviewSession",
    "JobRole",
    "Notification",
    "PasswordResetToken",
    "RefreshToken",
    "Resume",
    "ResumeVersion",
    "Role",
    "SkillScore",
    "User",
    "UserProfile",
    "UserRole",
]
