"""API tests for the JD-based practice interview endpoints.

We swap the lifecycle service dependency for a fake so the tests run fully
offline (no OpenAI, no Postgres). This validates:

- 401 without a session
- 403 when the current user is not a CANDIDATE
- happy path for start / get state / submit answer / submit coding / submit interview
- 422 when the request payload is malformed
- 404 (via the fake raising ``NotFoundError``) when the session belongs to
  another user
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.v1.candidate import interview_router
from app.api.v1.candidate.interview_router import get_lifecycle_service
from app.core.exceptions import AuthenticationError, NotFoundError, ValidationError
from app.main import create_app


def _candidate() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Ada Lovelace",
        email="ada@example.com",
        is_active=True,
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="CANDIDATE"))],
    )


def _admin() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Admin",
        email="admin@example.com",
        is_active=True,
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="ADMIN"))],
    )


def _made_question(
    *,
    number: int,
    text: str = "Explain the difference between SQL and NoSQL.",
    q_type: str = "TECHNICAL",
    answer_text: str | None = None,
) -> SimpleNamespace:
    """A duck-typed ``InterviewQuestion`` for the router serializer.

    Only the attributes ``_to_current_question`` touches are needed.
    """
    answer = None
    if answer_text is not None:
        answer = SimpleNamespace(answer_text=answer_text, is_submitted=True)
    return SimpleNamespace(
        id=uuid.uuid4(),
        question_number=number,
        question_text=text,
        question_type=q_type,
        difficulty="MEDIUM",
        topic="databases",
        skill="SQL",
        answer=answer,
    )


class _FakeService:
    """Duck-typed stand-in for ``InterviewLifecycleService``.

    Each test hands in the specific behavior it wants (via ``configure``) so
    every scenario controls the fake's return values.
    """

    def __init__(self) -> None:
        self._responses: dict[str, Any] = {}
        self._exceptions: dict[str, Exception] = {}
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def configure(self, method: str, *, returns: Any = None, raises: Exception | None = None) -> None:
        if raises is not None:
            self._exceptions[method] = raises
        else:
            self._responses[method] = returns

    async def _dispatch(self, method: str, **kwargs: Any) -> Any:
        self.calls.append((method, kwargs))
        if method in self._exceptions:
            raise self._exceptions[method]
        return self._responses.get(method)

    async def create_jd_practice(self, **kwargs: Any) -> Any:
        return await self._dispatch("create_jd_practice", **kwargs)

    async def create_role_practice(self, **kwargs: Any) -> Any:
        return await self._dispatch("create_role_practice", **kwargs)

    async def get_state(self, **kwargs: Any) -> Any:
        return await self._dispatch("get_state", **kwargs)

    async def get_practice_result(self, **kwargs: Any) -> Any:
        return await self._dispatch("get_practice_result", **kwargs)

    async def submit_answer(self, **kwargs: Any) -> Any:
        return await self._dispatch("submit_answer", **kwargs)

    async def submit_coding(self, **kwargs: Any) -> Any:
        return await self._dispatch("submit_coding", **kwargs)

    async def submit_interview(self, **kwargs: Any) -> Any:
        return await self._dispatch("submit_interview", **kwargs)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _install_fake(client: TestClient, service: _FakeService) -> None:
    client.app.dependency_overrides[get_lifecycle_service] = lambda: service


# ---------------------- POST /practice/jd-based ----------------------


def test_start_requires_authentication(client: TestClient) -> None:
    def _raise() -> SimpleNamespace:
        raise AuthenticationError("Authentication is required.")

    client.app.dependency_overrides[get_current_user] = _raise

    resp = client.post(
        "/api/v1/candidate/interviews/practice/jd-based",
        json={"job_description": "x" * 250},
    )

    assert resp.status_code == 401


def test_start_forbidden_for_admin(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = _admin

    resp = client.post(
        "/api/v1/candidate/interviews/practice/jd-based",
        json={"job_description": "x" * 250},
    )

    assert resp.status_code == 403


def test_start_happy_path(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    interview_id = uuid.uuid4()
    session_id = uuid.uuid4()
    first_q = _made_question(number=1, text="To start, tell me about your background.")
    fake.configure(
        "create_jd_practice",
        returns=SimpleNamespace(
            interview_id=interview_id,
            session_id=session_id,
            total_questions=7,
            duration_minutes=30,
            first_question=first_q,
        ),
    )
    _install_fake(client, fake)

    resp = client.post(
        "/api/v1/candidate/interviews/practice/jd-based",
        json={"job_description": "Backend engineer job description " * 20},
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["session_id"] == str(session_id)
    assert body["total_questions"] == 7
    assert body["current_question_number"] == 1
    assert body["current_question"]["question_text"].startswith("To start")
    assert body["current_question"]["existing_answer"] is None
    assert fake.calls[0][0] == "create_jd_practice"
    # No duration in body → service receives ``duration_minutes=None`` and
    # falls back to the platform default internally.
    assert fake.calls[0][1]["duration_minutes"] is None


def test_start_forwards_duration_minutes(client: TestClient) -> None:
    """Client-supplied duration must reach the service verbatim."""
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    fake.configure(
        "create_jd_practice",
        returns=SimpleNamespace(
            interview_id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            total_questions=9,
            duration_minutes=60,
            first_question=_made_question(number=1),
        ),
    )
    _install_fake(client, fake)

    resp = client.post(
        "/api/v1/candidate/interviews/practice/jd-based",
        json={
            "job_description": "Backend engineer job description " * 20,
            "duration_minutes": 60,
        },
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["total_questions"] == 9
    assert fake.calls[0][1]["duration_minutes"] == 60


def test_start_rejects_out_of_range_duration(client: TestClient) -> None:
    """Pydantic bounds return 422 before the service is even invoked."""
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate
    _install_fake(client, _FakeService())

    resp = client.post(
        "/api/v1/candidate/interviews/practice/jd-based",
        json={
            "job_description": "Backend engineer job description " * 20,
            "duration_minutes": 5,  # below the 15-minute floor
        },
    )

    assert resp.status_code == 422


def test_start_maps_domain_validation_error(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    fake.configure(
        "create_jd_practice",
        raises=ValidationError("Job description must be at least 200 characters."),
    )
    _install_fake(client, fake)

    resp = client.post(
        "/api/v1/candidate/interviews/practice/jd-based",
        json={"job_description": "short"},
    )

    assert resp.status_code == 422
    assert (
        resp.json()["error"]["message"]
        == "Job description must be at least 200 characters."
    )


# ---------------------- POST /practice/role-based ----------------------


def test_role_start_uses_authenticated_candidate_and_catalog_role(
    client: TestClient,
) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate
    fake = _FakeService()
    role_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fake.configure(
        "create_role_practice",
        returns=SimpleNamespace(
            interview_id=uuid.uuid4(),
            session_id=session_id,
            total_questions=7,
            duration_minutes=30,
            first_question=_made_question(
                number=1, text="Tell me about your AI engineering background."
            ),
            role_name="AI Engineer",
        ),
    )
    _install_fake(client, fake)

    response = client.post(
        "/api/v1/candidate/interviews/practice/role-based",
        json={"job_role_id": str(role_id), "duration_minutes": 30},
    )

    assert response.status_code == 201, response.text
    assert response.json()["interview"]["practice_type"] == "ROLE_BASED"
    assert response.json()["interview"]["role_name"] == "AI Engineer"
    call = fake.calls[0]
    assert call[0] == "create_role_practice"
    assert call[1]["candidate"] is candidate
    assert call[1]["job_role_id"] == role_id
    assert "candidate_id" not in call[1]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {
            "job_role_id": str(uuid.uuid4()),
            "custom_role_name": "Platform Engineer",
            "custom_requirements": ["Distributed systems"],
        },
        {"custom_role_name": "Platform Engineer"},
    ],
)
def test_role_start_rejects_missing_or_conflicting_role_inputs(
    client: TestClient, payload: dict[str, Any]
) -> None:
    client.app.dependency_overrides[get_current_user] = _candidate
    _install_fake(client, _FakeService())

    response = client.post(
        "/api/v1/candidate/interviews/practice/role-based",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("custom_requirements", ["x"] * 21),
        ("custom_requirements", ["x" * 301]),
        ("custom_skills", ["x"] * 31),
        ("custom_skills", ["x" * 101]),
    ],
)
def test_role_start_bounds_custom_role_lists_and_items(
    client: TestClient, field: str, value: list[str]
) -> None:
    client.app.dependency_overrides[get_current_user] = _candidate
    _install_fake(client, _FakeService())
    payload = {
        "custom_role_name": "Platform Engineer",
        "custom_requirements": ["Distributed systems"],
        "custom_skills": ["Python"],
        field: value,
    }

    response = client.post(
        "/api/v1/candidate/interviews/practice/role-based",
        json=payload,
    )

    assert response.status_code == 422


# ---------------------- GET /sessions/{id}/result ----------------------


def test_get_practice_result_returns_owned_persisted_evaluation(
    client: TestClient,
) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate
    session_id = uuid.uuid4()
    fake = _FakeService()
    fake.configure(
        "get_practice_result",
        returns=SimpleNamespace(
            session_id=session_id,
            status="completed",
            practice_type="ROLE_BASED",
            role_name="AI Engineer",
            overall_score=8.2,
            technical_score=8.5,
            communication_score=7.8,
            reasoning_score=8.0,
            project_knowledge_score=7.5,
            ai_verdict="CLEARED",
            confidence=0.88,
            summary="Strong role-aligned performance.",
            strengths=["Architecture trade-offs"],
            weaknesses=["Testing depth"],
            improvement_areas=["Add failure-mode analysis"],
            skill_scores=[],
        ),
    )
    _install_fake(client, fake)

    response = client.get(
        f"/api/v1/candidate/interviews/sessions/{session_id}/result"
    )

    assert response.status_code == 200, response.text
    assert response.json()["overall_score"] == 8.2
    assert fake.calls[0][1] == {
        "session_id": session_id,
        "candidate_id": candidate.id,
    }


def test_get_practice_result_scopes_foreign_session_to_404(
    client: TestClient,
) -> None:
    client.app.dependency_overrides[get_current_user] = _candidate
    fake = _FakeService()
    fake.configure(
        "get_practice_result",
        raises=NotFoundError("Interview session not found."),
    )
    _install_fake(client, fake)

    response = client.get(
        f"/api/v1/candidate/interviews/sessions/{uuid.uuid4()}/result"
    )

    assert response.status_code == 404


def test_get_practice_result_exposes_retryable_evaluation_status(
    client: TestClient,
) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate
    session_id = uuid.uuid4()
    fake = _FakeService()
    fake.configure(
        "get_practice_result",
        returns=SimpleNamespace(
            session_id=session_id,
            status="retryable",
            practice_type="ROLE_BASED",
            role_name="AI Engineer",
            strengths=[],
            weaknesses=[],
            improvement_areas=[],
            skill_scores=[],
        ),
    )
    _install_fake(client, fake)

    response = client.get(
        f"/api/v1/candidate/interviews/sessions/{session_id}/result"
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "retryable"


# ---------------------- GET /sessions/{id} ----------------------


def test_get_state_not_found_for_other_users_session(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    fake.configure("get_state", raises=NotFoundError("Interview session not found."))
    _install_fake(client, fake)

    resp = client.get(f"/api/v1/candidate/interviews/sessions/{uuid.uuid4()}")

    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_get_state_happy_path(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    session_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    current_q = _made_question(number=3, text="Explain indexes.", answer_text="btree")
    fake.configure(
        "get_state",
        returns=SimpleNamespace(
            session=SimpleNamespace(
                id=session_id,
                status="IN_PROGRESS",
                current_question_number=3,
                started_at=None,
            ),
            interview=SimpleNamespace(
                id=interview_id,
                interview_type="PRACTICE",
                practice_type="JD_BASED",
                role_name_snapshot=None,
                duration_minutes=30,
                status="IN_PROGRESS",
            ),
            total_questions=6,
            answered_count=2,
            current_question=current_q,
            is_last_question=False,
            can_submit=False,
        ),
    )
    _install_fake(client, fake)

    resp = client.get(f"/api/v1/candidate/interviews/sessions/{session_id}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == str(session_id)
    assert body["session_status"] == "IN_PROGRESS"
    assert body["total_questions"] == 6
    assert body["answered_count"] == 2
    assert body["current_question"]["question_number"] == 3
    assert body["current_question"]["existing_answer"] == "btree"


# ---------------------- POST /sessions/{id}/answers ----------------------


def test_submit_answer_returns_next_question(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    session_id = uuid.uuid4()
    question_id = uuid.uuid4()
    next_q = _made_question(number=4, text="What is a transaction?")
    fake.configure(
        "submit_answer",
        returns=SimpleNamespace(
            saved_answer=SimpleNamespace(id=uuid.uuid4()),
            next_question=next_q,
            is_last_question=False,
        ),
    )
    fake.configure(
        "get_state",
        returns=SimpleNamespace(
            session=SimpleNamespace(
                id=session_id,
                status="IN_PROGRESS",
                current_question_number=4,
                started_at=None,
            ),
            interview=SimpleNamespace(
                id=uuid.uuid4(),
                interview_type="PRACTICE",
                practice_type="JD_BASED",
                role_name_snapshot=None,
                duration_minutes=30,
                status="IN_PROGRESS",
            ),
            total_questions=6,
            answered_count=3,
            current_question=next_q,
            is_last_question=False,
            can_submit=False,
        ),
    )
    _install_fake(client, fake)

    resp = client.post(
        f"/api/v1/candidate/interviews/sessions/{session_id}/answers",
        json={
            "question_id": str(question_id),
            "answer_text": "My answer",
            "response_time_seconds": 42,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["next_question"]["question_number"] == 4
    assert body["is_last_question"] is False
    assert body["total_questions"] == 6
    assert body["answered_count"] == 3


def test_submit_answer_final_question(client: TestClient) -> None:
    """When the last plan slot has been answered, ``next_question`` is null."""
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    session_id = uuid.uuid4()
    question_id = uuid.uuid4()
    last_q = _made_question(number=6, text="Coding: reverse a string.", q_type="CODING")
    fake.configure(
        "submit_answer",
        returns=SimpleNamespace(
            saved_answer=SimpleNamespace(id=uuid.uuid4()),
            next_question=None,
            is_last_question=True,
        ),
    )
    fake.configure(
        "get_state",
        returns=SimpleNamespace(
            session=SimpleNamespace(
                id=session_id,
                status="IN_PROGRESS",
                current_question_number=6,
                started_at=None,
            ),
            interview=SimpleNamespace(
                id=uuid.uuid4(),
                interview_type="PRACTICE",
                practice_type="JD_BASED",
                role_name_snapshot=None,
                duration_minutes=30,
                status="IN_PROGRESS",
            ),
            total_questions=6,
            answered_count=6,
            current_question=last_q,
            is_last_question=True,
            can_submit=True,
        ),
    )
    _install_fake(client, fake)

    resp = client.post(
        f"/api/v1/candidate/interviews/sessions/{session_id}/answers",
        json={"question_id": str(question_id), "answer_text": "done"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["next_question"] is None
    assert body["is_last_question"] is True
    assert body["answered_count"] == 6


def test_submit_answer_validates_payload(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate
    fake = _FakeService()
    _install_fake(client, fake)

    resp = client.post(
        f"/api/v1/candidate/interviews/sessions/{uuid.uuid4()}/answers",
        json={"question_id": str(uuid.uuid4()), "answer_text": ""},
    )

    assert resp.status_code == 422


# ---------------------- POST /sessions/{id}/submit ----------------------


def test_submit_interview_schedules_evaluation(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    session_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    fake.configure(
        "submit_interview",
        returns=SimpleNamespace(
            session_id=session_id,
            interview_id=interview_id,
            status="EVALUATING",
            evaluation_status="pending",
            schedule_evaluation=True,
        ),
    )
    _install_fake(client, fake)

    resp = client.post(
        f"/api/v1/candidate/interviews/sessions/{session_id}/submit"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == str(session_id)
    assert body["status"] == "EVALUATING"
    assert body["evaluation_status"] == "pending"


def test_submit_interview_idempotent_when_already_evaluated(
    client: TestClient,
) -> None:
    """Duplicate submit — return ``ready`` without scheduling a new task."""
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    fake = _FakeService()
    session_id = uuid.uuid4()
    fake.configure(
        "submit_interview",
        returns=SimpleNamespace(
            session_id=session_id,
            interview_id=uuid.uuid4(),
            status="COMPLETED",
            evaluation_status="ready",
            schedule_evaluation=False,
        ),
    )
    _install_fake(client, fake)

    resp = client.post(
        f"/api/v1/candidate/interviews/sessions/{session_id}/submit"
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["evaluation_status"] == "ready"


def test_duplicate_submit_schedules_background_evaluator_once(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate
    fake = _FakeService()
    session_id = uuid.uuid4()
    interview_id = uuid.uuid4()
    scheduled: list[uuid.UUID] = []

    async def _record_scheduled(value: uuid.UUID) -> None:
        scheduled.append(value)

    monkeypatch.setattr(
        interview_router,
        "_run_evaluation_in_background",
        _record_scheduled,
    )
    _install_fake(client, fake)
    fake.configure(
        "submit_interview",
        returns=SimpleNamespace(
            session_id=session_id,
            interview_id=interview_id,
            status="EVALUATING",
            evaluation_status="pending",
            schedule_evaluation=True,
        ),
    )
    first = client.post(
        f"/api/v1/candidate/interviews/sessions/{session_id}/submit"
    )
    fake.configure(
        "submit_interview",
        returns=SimpleNamespace(
            session_id=session_id,
            interview_id=interview_id,
            status="EVALUATING",
            evaluation_status="pending",
            schedule_evaluation=False,
        ),
    )
    second = client.post(
        f"/api/v1/candidate/interviews/sessions/{session_id}/submit"
    )

    assert first.status_code == second.status_code == 200
    assert scheduled == [session_id]
