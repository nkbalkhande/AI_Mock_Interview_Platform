"""Request + response schemas for the JD-based practice interview API.

The interview flow is deliberately verbose on the response side: the frontend
needs a lot of context to render (progress bar, timer, question card, review
of past questions on refresh). Rather than one megaresponse, we split the
concerns and let the client compose:

- ``StartPracticeInterviewResponse`` — everything the player page needs on
  first load (session + interview + first question).
- ``SessionStateResponse`` — refresh / navigation loads (same shape, later
  questions).
- ``AnswerSubmissionResponse`` / ``CodingSubmissionResponse`` — mutation
  responses that return the *next* question inline so the client doesn't
  need a second round-trip.

All field names stay ``snake_case`` to match the rest of ``v1/candidate``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

MAX_ROLE_REQUIREMENTS = 20
MAX_ROLE_SKILLS = 30
MAX_REQUIREMENT_LENGTH = 300
MAX_SKILL_LENGTH = 100

RequirementItem = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_REQUIREMENT_LENGTH)
]
SkillItem = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SKILL_LENGTH)
]


class InterviewSummary(BaseModel):
    """Shallow interview metadata rendered in the player header."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    interview_type: str
    practice_type: str | None = None
    role_name: str | None = Field(
        default=None,
        description="For JD-based practice interviews this stays null; the "
        "player renders the JD summary instead.",
    )
    duration_minutes: int
    status: str
    started_at: datetime | None = None


class CurrentQuestion(BaseModel):
    """The question currently facing the candidate.

    ``expected_answer`` and ``evaluation_rubric`` are deliberately omitted —
    they would defeat the purpose of the interview. The evaluator uses them
    server-side.
    """

    id: uuid.UUID
    question_number: int
    question_text: str
    question_type: str
    difficulty: str | None = None
    topic: str | None = None
    skill: str | None = None
    existing_answer: str | None = Field(
        default=None,
        description=(
            "When the candidate refreshed after answering this question but "
            "before submitting the interview, we surface the previously "
            "typed answer so they don't lose their work."
        ),
    )


class StartPracticeInterviewRequest(BaseModel):
    job_description: str = Field(
        min_length=1,
        description=(
            "Full text of the job description. The service enforces min/max "
            "character bounds and returns a 422 with a helpful message."
        ),
    )
    duration_minutes: int | None = Field(
        default=None,
        ge=15,
        le=90,
        description=(
            "Desired interview duration in minutes. Drives the target "
            "question count and pacing signals sent to the planner. When "
            "omitted the service uses the platform default (30)."
        ),
    )


class JobRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    requirements: list[RequirementItem]
    skills: list[SkillItem]
    experience_min: float | None = None
    experience_max: float | None = None

    @field_validator("requirements", mode="before")
    @classmethod
    def normalize_requirements(cls, value: object) -> list[str]:
        return _normalize_bounded_strings(
            value, count=MAX_ROLE_REQUIREMENTS, item_length=MAX_REQUIREMENT_LENGTH
        )

    @field_validator("skills", mode="before")
    @classmethod
    def normalize_skills(cls, value: object) -> list[str]:
        return _normalize_bounded_strings(
            value, count=MAX_ROLE_SKILLS, item_length=MAX_SKILL_LENGTH
        )


class StartRolePracticeInterviewRequest(BaseModel):
    job_role_id: uuid.UUID | None = None
    custom_role_name: str | None = Field(default=None, min_length=2, max_length=150)
    custom_requirements: list[RequirementItem] | None = Field(
        default=None, min_length=1, max_length=MAX_ROLE_REQUIREMENTS
    )
    custom_skills: list[SkillItem] = Field(
        default_factory=list, max_length=MAX_ROLE_SKILLS
    )
    duration_minutes: int | None = Field(default=None, ge=15, le=90)

    @model_validator(mode="after")
    def validate_role_selection(self) -> "StartRolePracticeInterviewRequest":
        has_catalog = self.job_role_id is not None
        has_custom = self.custom_role_name is not None
        if has_catalog == has_custom:
            raise ValueError(
                "Choose exactly one catalog role or provide one custom role."
            )
        if has_catalog and (
            self.custom_requirements is not None or self.custom_skills
        ):
            raise ValueError("Custom role fields cannot accompany a catalog role.")
        if has_custom and not self.custom_requirements:
            raise ValueError("Custom role requirements are required.")
        return self


def _normalize_bounded_strings(
    value: object, *, count: int, item_length: int
) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if not cleaned or len(cleaned) > item_length:
            continue
        normalized.append(cleaned)
        if len(normalized) >= count:
            break
    return normalized


class StartPracticeInterviewResponse(BaseModel):
    interview: InterviewSummary
    session_id: uuid.UUID
    total_questions: int
    current_question_number: int
    current_question: CurrentQuestion


class SessionStateResponse(BaseModel):
    """Everything needed to render the interview player mid-session.

    ``current_question`` is null when the session has been submitted; the
    frontend interprets that as "session finished, redirect to results".
    """

    interview: InterviewSummary
    session_id: uuid.UUID
    session_status: str
    total_questions: int
    answered_count: int
    current_question_number: int
    current_question: CurrentQuestion | None
    is_last_question: bool
    can_submit: bool
    timed_out: bool = False


class AnswerSubmissionRequest(BaseModel):
    question_id: uuid.UUID
    answer_text: str = Field(min_length=1, max_length=20000)
    response_time_seconds: int | None = Field(default=None, ge=0)


class CodingSubmissionRequest(BaseModel):
    question_id: uuid.UUID
    code: str = Field(min_length=1, max_length=50000)
    language: str = Field(min_length=1, max_length=50)


class AnswerSubmissionResponse(BaseModel):
    """Response shape for both text and coding answer submissions."""

    next_question: CurrentQuestion | None
    is_last_question: bool
    total_questions: int
    answered_count: int


class SubmitInterviewResponse(BaseModel):
    """Returned by ``POST /sessions/{id}/submit``.

    Includes the session id so the frontend can immediately route to the
    result page (which polls until evaluation is done).
    """

    session_id: uuid.UUID
    interview_id: uuid.UUID
    status: str
    evaluation_status: str = Field(
        description=(
            "One of ``pending`` (evaluation just scheduled) or ``ready`` "
            "(evaluation already exists — e.g. duplicate submit)."
        ),
    )


class PracticeSkillScore(BaseModel):
    skill_name: str
    score: float
    max_score: float
    strength: str | None = None
    improvement_area: str | None = None
    evidence: list[str]


class PracticeResultResponse(BaseModel):
    session_id: uuid.UUID
    status: Literal["pending", "retryable", "completed"]
    practice_type: str
    role_name: str | None = None
    overall_score: float | None = None
    technical_score: float | None = None
    communication_score: float | None = None
    reasoning_score: float | None = None
    project_knowledge_score: float | None = None
    ai_verdict: str | None = None
    confidence: float | None = None
    summary: str | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list)
    skill_scores: list[PracticeSkillScore] = Field(default_factory=list)
