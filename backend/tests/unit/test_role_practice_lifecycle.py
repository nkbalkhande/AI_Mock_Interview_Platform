from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest

from app.models.interview import Interview
from app.models.interview_session import InterviewSession
from app.services.interviews.lifecycle_service import InterviewLifecycleService
from app.services.interviews.question_planner import PlannedQuestion
from app.services.resumes.current_resume_loader import CurrentResume


class _FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, value: Any) -> None:
        if getattr(value, "id", None) is None:
            value.id = uuid.uuid4()
        self.added.append(value)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        return None


class _Planner:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] = {}

    async def plan_next(self, **kwargs: Any) -> PlannedQuestion:
        self.kwargs = kwargs
        return PlannedQuestion(
            question_text="Tell me about your relevant experience.",
            question_type="BEHAVIORAL",
            stage="INTRODUCTION",
            difficulty="EASY",
            topic="introduction",
            skill="communication",
            expected_answer="A concise role-relevant summary.",
            evaluation_rubric="Clear and relevant.",
            prompt_version="question_planner_v3",
            model_name="",
        )


class _Events:
    async def record(self, **_: Any) -> None:
        return None


@pytest.mark.asyncio
async def test_catalog_role_start_snapshots_role_resume_and_profile() -> None:
    db = _FakeSession()
    planner = _Planner()
    service = InterviewLifecycleService(
        db,  # type: ignore[arg-type]
        planner=planner,  # type: ignore[arg-type]
        evaluator=SimpleNamespace(),
        model_name="test-model",
    )
    role_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate = SimpleNamespace(
        id=uuid.uuid4(),
        profile=SimpleNamespace(
            current_designation="ML Engineer",
            years_of_experience=Decimal("4.50"),
        ),
    )
    service._job_roles = SimpleNamespace(  # type: ignore[assignment]
        get_active=lambda _: None
    )

    async def _get_role(_: uuid.UUID) -> SimpleNamespace:
        return SimpleNamespace(
            id=role_id,
            name="AI Engineer",
            requirements=[
                "Production AI delivery",
                42,
                {"nested": "invalid"},
                "",
                "x" * 301,
                *[f"Requirement {index}" for index in range(30)],
            ],
            skills=[
                "Python",
                ["nested"],
                None,
                "",
                "x" * 101,
                "MLOps",
                *[f"Skill {index}" for index in range(35)],
            ],
            experience_min=Decimal("2"),
            experience_max=Decimal("8"),
        )

    async def _get_resume(_: uuid.UUID) -> CurrentResume:
        return CurrentResume(
            version_id=resume_id,
            extracted_text="Built and monitored forecasting services.",
            file_name="resume.pdf",
        )

    service._job_roles.get_active = _get_role
    service._resume_loader = SimpleNamespace(  # type: ignore[assignment]
        get_current_for_user=_get_resume
    )
    service._events = _Events()  # type: ignore[assignment]

    started = await service.create_role_practice(
        candidate=candidate,
        job_role_id=role_id,
        custom_role_name=None,
        custom_requirements=None,
        custom_skills=None,
        duration_minutes=30,
    )

    interview = next(item for item in db.added if isinstance(item, Interview))
    session = next(item for item in db.added if isinstance(item, InterviewSession))
    assert interview.practice_type == "ROLE_BASED"
    assert interview.job_role_id == role_id
    assert interview.role_name_snapshot == "AI Engineer"
    assert interview.resume_version_id == resume_id
    role_snapshot = session.interview_state["role_snapshot"]
    assert len(role_snapshot["requirements"]) == 20
    assert role_snapshot["requirements"][0] == "Production AI delivery"
    assert all(
        isinstance(item, str) and len(item) <= 300
        for item in role_snapshot["requirements"]
    )
    assert len(role_snapshot["skills"]) == 30
    assert role_snapshot["skills"][:2] == ["Python", "MLOps"]
    assert all(
        isinstance(item, str) and len(item) <= 100
        for item in role_snapshot["skills"]
    )
    assert session.interview_state["candidate_designation"] == "ML Engineer"
    assert session.interview_state["resume_snippet"].startswith("Built and monitored")
    assert planner.kwargs["target_context"].kind == "ROLE"
    assert "Production AI delivery" in planner.kwargs["target_context"].content
    assert started.role_name == "AI Engineer"
