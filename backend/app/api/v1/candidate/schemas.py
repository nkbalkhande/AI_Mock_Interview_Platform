"""Response schemas for the candidate dashboard API.

Kept as plain DTOs (``BaseModel``) rather than SQLAlchemy-mapped read models
so the wire shape can diverge from the ORM without breaking clients — the
dashboard aggregates data from six tables into three response envelopes,
so a hand-rolled DTO layer is the right seam.

Field naming stays ``snake_case`` to match the auth API (client-side mapping
to ``camelCase`` happens in the frontend feature module, consistent with
``features/auth``).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CandidateProfileSummary(BaseModel):
    """Minimal profile fields the dashboard header uses (name + avatar)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: str
    current_designation: str | None = None
    current_organization: str | None = None
    years_of_experience: Decimal | None = None
    profile_photo_path: str | None = None


class CandidateProfileResponse(BaseModel):
    """Full candidate profile for the candidate profile page."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    full_name: str
    email: EmailStr
    current_designation: str | None = None
    current_organization: str | None = None
    years_of_experience: Decimal | None = None
    phone_number: str | None = None
    bio: str | None = None
    profile_photo_path: str | None = None


class CandidateProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    current_organization: str = Field(min_length=1, max_length=200)
    current_designation: str = Field(min_length=1, max_length=150)
    years_of_experience: Annotated[
        Decimal,
        Field(ge=0, le=Decimal("99.99"), max_digits=4, decimal_places=2),
    ]
    phone_number: str | None = Field(default=None, max_length=30)
    bio: str | None = Field(default=None, max_length=1000)


class DashboardStats(BaseModel):
    """Aggregate counts + score shown as tiles at the top of the dashboard."""

    practice_interviews: int = Field(ge=0)
    upcoming_interviews: int = Field(ge=0)
    completed_interviews: int = Field(ge=0)
    average_practice_score: Decimal | None = Field(
        default=None,
        description=(
            "Average FINAL overall_score across PRACTICE interviews only "
            "(0-10 scale). Null when the candidate has no evaluated practice "
            "runs yet."
        ),
    )


class DashboardResponse(BaseModel):
    profile: CandidateProfileSummary
    stats: DashboardStats


class UpcomingInterview(BaseModel):
    """Single row in the Upcoming Interviews section."""

    id: uuid.UUID
    role: str | None = Field(
        default=None, description="Snapshotted role name at assignment time."
    )
    organization: str | None = Field(
        default=None,
        description=(
            "Assigning organization if known. Derived from the assigning "
            "admin's ``current_organization`` where available."
        ),
    )
    job_description: str | None = None
    required_experience_min: Decimal | None = None
    required_experience_max: Decimal | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = None
    duration_minutes: int
    status: str
    access_state: str = Field(
        description=(
            "PENDING before access_start_at, OPEN inside the window, "
            "CLOSED after access_end_at. Frontend uses this to decide "
            "whether to render the [Join Interview] CTA."
        )
    )
    access_start_at: datetime | None = None
    access_end_at: datetime | None = None


class UpcomingInterviewsResponse(BaseModel):
    items: list[UpcomingInterview]


class UpcomingInterviewDetail(BaseModel):
    """Full details for a single assigned interview the candidate is about to join."""

    id: uuid.UUID
    role: str | None = None
    organization: str | None = None
    job_description: str | None = None
    required_experience_min: Decimal | None = None
    required_experience_max: Decimal | None = None
    scheduled_at: datetime | None = None
    timezone: str | None = None
    duration_minutes: int
    status: str
    access_state: str
    access_start_at: datetime | None = None
    access_end_at: datetime | None = None
    instructions: str | None = Field(
        default=None,
        description="Admin-provided instructions/notes for the candidate.",
    )
    assigned_by_name: str | None = Field(
        default=None,
        description="Full name of the admin/interviewer who assigned this interview.",
    )


class PracticeResultSummary(BaseModel):
    """Compact summary of a completed PRACTICE interview."""

    interview_id: uuid.UUID
    session_id: uuid.UUID | None = None
    role: str | None = None
    completed_at: datetime | None = None
    overall_score: Decimal | None = None
    technical_score: Decimal | None = None
    communication_score: Decimal | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class AssignedResultSummary(BaseModel):
    """Compact summary of a completed ASSIGNED interview."""

    interview_id: uuid.UUID
    session_id: uuid.UUID | None = None
    role: str | None = None
    completed_at: datetime | None = None
    ai_overall_score: Decimal | None = None
    ai_verdict: str | None = None
    admin_decision: str | None = None
    admin_feedback: str | None = None
    result_published_at: datetime | None = None


class RecentResultsResponse(BaseModel):
    """Recent results split by interview type so the frontend can render each
    section without re-partitioning the list."""

    practice: list[PracticeResultSummary]
    assigned: list[AssignedResultSummary]


class PracticeResultListItem(BaseModel):
    """Row in the full practice results list (richer than dashboard summary)."""

    interview_id: uuid.UUID
    session_id: uuid.UUID | None = None
    practice_type: str | None = Field(
        default=None, description="JD_BASED or ROLE_BASED"
    )
    role: str | None = None
    duration_minutes: int | None = None
    completed_at: datetime | None = None
    overall_score: Decimal | None = None
    technical_score: Decimal | None = None
    communication_score: Decimal | None = None
    reasoning_score: Decimal | None = None
    project_knowledge_score: Decimal | None = None
    ai_verdict: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class PracticeResultListResponse(BaseModel):
    """Paginated list of all practice results."""

    items: list[PracticeResultListItem]
    total: int
    page: int
    page_size: int


class AssignedResultListItem(BaseModel):
    """Row in the full assigned results list."""

    interview_id: uuid.UUID
    session_id: uuid.UUID | None = None
    role: str | None = None
    duration_minutes: int | None = None
    completed_at: datetime | None = None
    ai_overall_score: Decimal | None = None
    ai_verdict: str | None = None
    admin_decision: str | None = None
    admin_feedback: str | None = None
    result_published_at: datetime | None = None


class AssignedResultListResponse(BaseModel):
    """Paginated list of all assigned results."""

    items: list[AssignedResultListItem]
    total: int
    page: int
    page_size: int


class AssignedResultDetail(BaseModel):
    """Result view for a single assigned interview session.

    Assigned results are only revealed after the admin submits the final
    decision. Until then ``status`` is ``PENDING_REVIEW`` and every AI/admin
    field stays null — the AI recommendation must never reach the candidate
    ahead of the admin's decision.
    """

    interview_id: uuid.UUID
    session_id: uuid.UUID
    role: str | None = None
    duration_minutes: int | None = None
    scheduled_at: datetime | None = None
    completed_at: datetime | None = None
    assigned_by_name: str | None = None
    status: str = Field(description="PENDING_REVIEW or PUBLISHED")
    ai_overall_score: Decimal | None = None
    ai_verdict: str | None = None
    ai_summary: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    admin_decision: str | None = None
    admin_feedback: str | None = None
    decided_by_name: str | None = None
    result_published_at: datetime | None = None


# ── Interview History ────────────────────────────────────────────────────

class InterviewHistoryItem(BaseModel):
    """One row in the candidate's full interview history list."""

    interview_id: uuid.UUID
    session_id: uuid.UUID | None = None
    interview_type: str = Field(description="PRACTICE or ASSIGNED")
    practice_type: str | None = Field(
        default=None, description="JD_BASED or ROLE_BASED (practice only)"
    )
    role: str | None = None
    display_status: str = Field(
        description=(
            "User-friendly status: Completed, In Progress, Evaluating, "
            "Submitted, Abandoned, Cancelled, Expired, Not Started"
        )
    )
    interview_status: str = Field(description="Raw interview.status value")
    session_status: str | None = Field(
        default=None, description="Raw session.status value"
    )
    can_resume: bool = Field(
        default=False,
        description="True only while an unfinished interview is inside its access window.",
    )
    started_at: datetime | None = None
    last_activity_at: datetime | None = None
    duration_minutes: int
    overall_score: Decimal | None = None
    answered_count: int = 0
    total_questions: int = 0


class InterviewHistoryResponse(BaseModel):
    """Paginated interview history with total for the frontend paginator."""

    items: list[InterviewHistoryItem]
    total: int
    page: int
    page_size: int
