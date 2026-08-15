from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models.interview import Interview
from app.models.interview_session import InterviewSession
from app.services.interviews.lifecycle_service import InterviewLifecycleService
from app.services.interviews.question_planner import PlannedQuestion


class _FakeDb:
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
        self.calls = 0
        self.kwargs: dict[str, Any] = {}

    async def plan_next(self, **kwargs: Any) -> PlannedQuestion:
        self.calls += 1
        self.kwargs = kwargs
        return PlannedQuestion(
            question_text="Tell me about a production system you owned.",
            question_type="BEHAVIORAL",
            stage="INTRODUCTION",
            difficulty="EASY",
            topic="introduction",
            skill="communication",
            expected_answer="A concise ownership story.",
            evaluation_rubric="Clear and relevant.",
            prompt_version="question_planner_v3",
            model_name="",
        )


class _Events:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


class _Interviews:
    def __init__(self, interview: Any) -> None:
        self.interview = interview

    async def get_owned_for_start(self, *_: Any) -> Any:
        return self.interview


def _open_window() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    return now - timedelta(minutes=5), now + timedelta(minutes=40)


def _assigned_interview(
    *,
    candidate_id: uuid.UUID,
    status: str = "ASSIGNED",
    sessions: list[Any] | None = None,
    resume: bool = True,
    window: str = "open",
) -> Interview:
    now = datetime.now(timezone.utc)
    if window == "pending":
        start, end = now + timedelta(minutes=10), now + timedelta(minutes=50)
    elif window == "closed":
        start, end = now - timedelta(minutes=90), now - timedelta(minutes=5)
    else:
        start, end = _open_window()

    interview = Interview(
        candidate_id=candidate_id,
        interview_type="ASSIGNED",
        practice_type=None,
        role_name_snapshot="Backend Engineer",
        job_description_snapshot=(
            "Build and operate FastAPI services with PostgreSQL and Redis."
        ),
        duration_minutes=30,
        status=status,
        access_start_at=start,
        access_end_at=end,
    )
    interview.id = uuid.uuid4()
    if resume:
        resume_id = uuid.uuid4()
        interview.resume_version_id = resume_id
        interview.resume_version = SimpleNamespace(  # type: ignore[assignment]
            id=resume_id,
            extracted_text="Shipped FastAPI services in production.",
            file_name="resume.pdf",
        )
    else:
        interview.resume_version = None  # type: ignore[assignment]
    interview.sessions = sessions or []  # type: ignore[assignment]
    return interview


def _service(db: _FakeDb, interview: Any) -> InterviewLifecycleService:
    planner = _Planner()
    service = InterviewLifecycleService(
        db,  # type: ignore[arg-type]
        planner=planner,  # type: ignore[arg-type]
        evaluator=SimpleNamespace(),
        model_name="test-model",
    )
    service._interviews = _Interviews(interview)  # type: ignore[assignment]
    service._events = _Events()  # type: ignore[assignment]
    service._planner = planner  # type: ignore[assignment]
    return service


@pytest.mark.asyncio
async def test_start_assigned_creates_session_from_frozen_jd_and_resume() -> None:
    db = _FakeDb()
    candidate = SimpleNamespace(
        id=uuid.uuid4(),
        profile=SimpleNamespace(
            current_designation="Backend Engineer",
            years_of_experience=4,
        ),
    )
    interview = _assigned_interview(candidate_id=candidate.id)
    service = _service(db, interview)

    started = await service.start_assigned(
        candidate=candidate, interview_id=interview.id
    )

    session = next(item for item in db.added if isinstance(item, InterviewSession))
    assert started.session_id == session.id
    assert interview.status == "IN_PROGRESS"
    assert session.status == "IN_PROGRESS"
    assert session.interview_state["target_context"]["kind"] == "JD"
    assert "FastAPI" in session.interview_state["target_context"]["content"]
    assert session.interview_state["resume_snippet"].startswith("Shipped FastAPI")
    assert service._planner.calls == 1  # type: ignore[union-attr]
    assert any(
        call["event_type"] == "INTERVIEW_STARTED" for call in service._events.calls
    )


@pytest.mark.asyncio
async def test_start_assigned_resumes_existing_session_without_replanning() -> None:
    db = _FakeDb()
    candidate = SimpleNamespace(id=uuid.uuid4(), profile=None)
    question = SimpleNamespace(
        id=uuid.uuid4(),
        question_number=2,
        question_text="How do you design retries?",
        question_type="TECHNICAL",
        difficulty="MEDIUM",
        topic="reliability",
        skill="backend",
        answer=None,
    )
    session = SimpleNamespace(
        id=uuid.uuid4(),
        attempt_number=1,
        status="IN_PROGRESS",
        started_at=datetime.now(timezone.utc),
        interview_state={"total_target_questions": 7, "duration_minutes": 30},
        questions=[question],
    )
    now = datetime.now(timezone.utc)
    interview = SimpleNamespace(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        interview_type="ASSIGNED",
        status="IN_PROGRESS",
        role_name_snapshot="Backend Engineer",
        job_description_snapshot="Build FastAPI services.",
        duration_minutes=30,
        access_start_at=now - timedelta(minutes=5),
        access_end_at=now + timedelta(minutes=40),
        resume_version=SimpleNamespace(
            id=uuid.uuid4(),
            extracted_text="Shipped APIs.",
            file_name="resume.pdf",
        ),
        sessions=[session],
    )
    service = _service(db, interview)

    started = await service.start_assigned(
        candidate=candidate, interview_id=interview.id
    )

    assert started.session_id == session.id
    assert started.first_question.question_number == 2
    assert service._planner.calls == 0  # type: ignore[union-attr]
    assert not any(isinstance(item, InterviewSession) for item in db.added)


@pytest.mark.asyncio
async def test_start_assigned_rejects_pending_window() -> None:
    candidate = SimpleNamespace(id=uuid.uuid4(), profile=None)
    interview = _assigned_interview(candidate_id=candidate.id, window="pending")
    service = _service(_FakeDb(), interview)

    with pytest.raises(BusinessRuleError, match="not yet available"):
        await service.start_assigned(candidate=candidate, interview_id=interview.id)


@pytest.mark.asyncio
async def test_start_assigned_rejects_closed_window() -> None:
    candidate = SimpleNamespace(id=uuid.uuid4(), profile=None)
    interview = _assigned_interview(candidate_id=candidate.id, window="closed")
    service = _service(_FakeDb(), interview)

    with pytest.raises(BusinessRuleError, match="has closed"):
        await service.start_assigned(candidate=candidate, interview_id=interview.id)


@pytest.mark.asyncio
async def test_start_assigned_not_found_for_missing_or_practice() -> None:
    candidate = SimpleNamespace(id=uuid.uuid4(), profile=None)
    service = _service(_FakeDb(), None)

    with pytest.raises(NotFoundError):
        await service.start_assigned(
            candidate=candidate, interview_id=uuid.uuid4()
        )


@pytest.mark.asyncio
async def test_start_assigned_rejects_already_submitted() -> None:
    candidate = SimpleNamespace(id=uuid.uuid4(), profile=None)
    interview = _assigned_interview(
        candidate_id=candidate.id, status="SUBMITTED", window="open"
    )
    service = _service(_FakeDb(), interview)

    with pytest.raises(ConflictError, match="already been submitted"):
        await service.start_assigned(candidate=candidate, interview_id=interview.id)


@pytest.mark.asyncio
async def test_start_assigned_requires_resume_snapshot() -> None:
    candidate = SimpleNamespace(id=uuid.uuid4(), profile=None)
    interview = _assigned_interview(
        candidate_id=candidate.id, resume=False, window="open"
    )
    service = _service(_FakeDb(), interview)

    with pytest.raises(BusinessRuleError, match="resume"):
        await service.start_assigned(candidate=candidate, interview_id=interview.id)
