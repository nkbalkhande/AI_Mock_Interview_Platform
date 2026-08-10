"""Request/response schemas for the admin API.

DTOs are kept as plain ``BaseModel`` subclasses so the wire shape can diverge
from the ORM without breaking clients.  Field naming stays ``snake_case`` to
match the candidate API convention.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class AdminDashboardStats(BaseModel):
    total_candidates: int = Field(ge=0)
    total_interviews: int = Field(ge=0)
    pending_evaluations: int = Field(ge=0)
    completed_interviews: int = Field(ge=0)


class RecentActivityItem(BaseModel):
    id: uuid.UUID
    event_type: str
    description: str
    actor_name: str | None = None
    created_at: datetime


class AdminDashboardResponse(BaseModel):
    stats: AdminDashboardStats
    recent_activity: list[RecentActivityItem]


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    is_active: bool
    email_verified: bool
    roles: list[str] = Field(default_factory=list)
    current_organization: str | None = None
    current_designation: str | None = None
    years_of_experience: Decimal | None = None
    created_at: datetime
    last_login_at: datetime | None = None


class UserListResponse(BaseModel):
    items: list[UserListItem]
    total: int
    page: int
    page_size: int


class UserInterviewSummary(BaseModel):
    interview_id: uuid.UUID
    interview_type: str
    role: str | None = None
    status: str
    scheduled_at: datetime | None = None
    created_at: datetime


class UserDetailResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: str
    is_active: bool
    email_verified: bool
    roles: list[str] = Field(default_factory=list)
    current_organization: str | None = None
    current_designation: str | None = None
    years_of_experience: Decimal | None = None
    phone_number: str | None = None
    bio: str | None = None
    profile_photo_path: str | None = None
    created_at: datetime
    last_login_at: datetime | None = None
    total_interviews: int = 0
    interviews: list[UserInterviewSummary] = Field(default_factory=list)


class UpdateUserStatusRequest(BaseModel):
    is_active: bool


class UpdateUserStatusResponse(BaseModel):
    id: uuid.UUID
    is_active: bool


# ---------------------------------------------------------------------------
# Interviews
# ---------------------------------------------------------------------------

class InterviewListItem(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    interview_type: str
    practice_type: str | None = None
    role: str | None = None
    status: str
    scheduled_at: datetime | None = None
    duration_minutes: int
    assigned_by_name: str | None = None
    created_at: datetime


class InterviewListResponse(BaseModel):
    items: list[InterviewListItem]
    total: int
    page: int
    page_size: int


class InterviewDetailResponse(BaseModel):
    id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    interview_type: str
    practice_type: str | None = None
    role: str | None = None
    job_description: str | None = None
    role_requirements: str | None = None
    required_experience_min: Decimal | None = None
    required_experience_max: Decimal | None = None
    status: str
    scheduled_at: datetime | None = None
    timezone: str | None = None
    duration_minutes: int
    access_start_at: datetime | None = None
    access_end_at: datetime | None = None
    instructions: str | None = None
    assigned_by_name: str | None = None
    created_at: datetime
    updated_at: datetime


class AssignInterviewRequest(BaseModel):
    candidate_id: uuid.UUID
    job_role_id: uuid.UUID | None = Field(
        default=None,
        description="Optional job_role to pull name/requirements from.",
    )
    role_name: str = Field(min_length=1, max_length=150)
    job_description: str = Field(min_length=1)
    role_requirements: str | None = None
    required_experience_min: Decimal | None = Field(default=None, ge=0)
    required_experience_max: Decimal | None = Field(default=None, ge=0)
    scheduled_at: datetime
    timezone: str = Field(default="UTC", max_length=100)
    duration_minutes: int = Field(default=30, gt=0, le=180)
    instructions: str | None = None


class AssignInterviewResponse(BaseModel):
    id: uuid.UUID
    status: str
    candidate_name: str
    role: str | None = None
    scheduled_at: datetime | None = None
    message: str = "Interview assigned successfully."


# ---------------------------------------------------------------------------
# Evaluations
# ---------------------------------------------------------------------------

class EvaluationListItem(BaseModel):
    session_id: uuid.UUID
    interview_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    role: str | None = None
    interview_type: str
    ai_overall_score: Decimal | None = None
    ai_verdict: str | None = None
    status: str
    submitted_at: datetime | None = None


class EvaluationListResponse(BaseModel):
    items: list[EvaluationListItem]
    total: int
    page: int
    page_size: int


class QuestionEvaluationDetail(BaseModel):
    question_number: int
    question_text: str
    question_type: str
    difficulty: str | None = None
    candidate_answer: str | None = None
    expected_answer: str | None = None
    correctness_score: Decimal | None = None
    technical_score: Decimal | None = None
    communication_score: Decimal | None = None
    reasoning_score: Decimal | None = None
    overall_score: Decimal | None = None
    feedback: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class EvaluationDetailResponse(BaseModel):
    session_id: uuid.UUID
    interview_id: uuid.UUID
    candidate_name: str
    candidate_email: str
    role: str | None = None
    interview_type: str
    practice_type: str | None = None
    duration_minutes: int
    scheduled_at: datetime | None = None

    # AI final evaluation
    ai_overall_score: Decimal | None = None
    ai_verdict: str | None = None
    ai_confidence: Decimal | None = None
    ai_summary: str | None = None
    ai_strengths: list[str] = Field(default_factory=list)
    ai_weaknesses: list[str] = Field(default_factory=list)
    ai_improvement_areas: list[str] = Field(default_factory=list)

    # Existing admin decision (if any)
    admin_decision: str | None = None
    admin_feedback: str | None = None
    decided_by_name: str | None = None
    decided_at: datetime | None = None

    # Per-question breakdown
    questions: list[QuestionEvaluationDetail] = Field(default_factory=list)

    session_status: str
    session_started_at: datetime | None = None
    session_ended_at: datetime | None = None


class SubmitDecisionRequest(BaseModel):
    admin_decision: str = Field(
        description="CLEARED, NOT_CLEARED, or NEEDS_FURTHER_REVIEW"
    )
    admin_feedback: str | None = Field(
        default=None,
        description="Free-form feedback visible to the candidate.",
    )


class SubmitDecisionResponse(BaseModel):
    session_id: uuid.UUID
    admin_decision: str
    decided_at: datetime
    message: str = "Decision submitted successfully."


# ---------------------------------------------------------------------------
# Job Roles (read-only for admin)
# ---------------------------------------------------------------------------

class JobRoleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    requirements: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_min: Decimal | None = None
    experience_max: Decimal | None = None
    is_active: bool
