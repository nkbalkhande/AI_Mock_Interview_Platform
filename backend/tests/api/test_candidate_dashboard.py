"""API tests for the candidate dashboard endpoints.

Both the auth dependency and the service dependency are overridden with fakes
so the tests run fully offline. This validates:
- 401 without a session
- 403 when the current user is not a candidate
- happy-path shapes for /dashboard, /upcoming-interviews, /recent-results
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.v1.candidate.router import get_candidate_dashboard_service
from app.api.v1.candidate.schemas import (
    AssignedResultSummary,
    CandidateProfileSummary,
    DashboardResponse,
    DashboardStats,
    PracticeResultSummary,
    RecentResultsResponse,
    UpcomingInterview,
    UpcomingInterviewsResponse,
)
from app.core.exceptions import AuthenticationError
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


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_dashboard_requires_authentication(client: TestClient) -> None:
    def _raise() -> SimpleNamespace:
        raise AuthenticationError("Authentication is required.")

    client.app.dependency_overrides[get_current_user] = _raise

    resp = client.get("/api/v1/candidate/dashboard")

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_error"


def test_dashboard_forbidden_for_admin(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = _admin

    resp = client.get("/api/v1/candidate/dashboard")

    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "permission_denied"


def test_dashboard_returns_stats_and_profile(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    dashboard_payload = DashboardResponse(
        profile=CandidateProfileSummary(
            id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            current_designation="Software Engineer",
            current_organization="Acme Inc.",
            years_of_experience=Decimal("3.5"),
            profile_photo_path=None,
        ),
        stats=DashboardStats(
            practice_interviews=4,
            upcoming_interviews=1,
            completed_interviews=2,
            average_practice_score=Decimal("7.25"),
        ),
    )

    class _FakeService:
        async def get_dashboard(self, _user: SimpleNamespace) -> DashboardResponse:
            return dashboard_payload

    client.app.dependency_overrides[get_candidate_dashboard_service] = (
        lambda: _FakeService()
    )

    resp = client.get("/api/v1/candidate/dashboard")

    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["email"] == "ada@example.com"
    assert body["profile"]["current_designation"] == "Software Engineer"
    assert body["stats"]["practice_interviews"] == 4
    assert body["stats"]["upcoming_interviews"] == 1
    assert body["stats"]["average_practice_score"] == "7.25"


def test_upcoming_interviews_returns_access_state(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    now = datetime.now(timezone.utc)
    upcoming = UpcomingInterviewsResponse(
        items=[
            UpcomingInterview(
                id=uuid.uuid4(),
                role="Backend Engineer",
                organization=None,
                job_description="Build APIs.",
                required_experience_min=Decimal("2.00"),
                required_experience_max=Decimal("5.00"),
                scheduled_at=now + timedelta(hours=2),
                timezone="UTC",
                duration_minutes=45,
                status="SCHEDULED",
                access_state="PENDING",
                access_start_at=now + timedelta(hours=2) - timedelta(minutes=5),
                access_end_at=now + timedelta(hours=2) + timedelta(minutes=10),
            )
        ]
    )

    class _FakeService:
        async def get_upcoming_interviews(
            self, _user: SimpleNamespace, *, limit: int
        ) -> UpcomingInterviewsResponse:
            assert limit == 20
            return upcoming

    client.app.dependency_overrides[get_candidate_dashboard_service] = (
        lambda: _FakeService()
    )

    resp = client.get("/api/v1/candidate/upcoming-interviews")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["role"] == "Backend Engineer"
    assert item["access_state"] == "PENDING"
    assert item["duration_minutes"] == 45


def test_recent_results_returns_split_lists(client: TestClient) -> None:
    candidate = _candidate()
    client.app.dependency_overrides[get_current_user] = lambda: candidate

    now = datetime.now(timezone.utc)
    payload = RecentResultsResponse(
        practice=[
            PracticeResultSummary(
                interview_id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                role="Data Scientist",
                completed_at=now,
                overall_score=Decimal("8.20"),
                technical_score=Decimal("8.50"),
                communication_score=Decimal("7.75"),
                strengths=["Clear reasoning"],
                weaknesses=["Rushed on system design"],
            )
        ],
        assigned=[
            AssignedResultSummary(
                interview_id=uuid.uuid4(),
                session_id=uuid.uuid4(),
                role="Data Engineer",
                completed_at=now,
                ai_overall_score=Decimal("7.10"),
                ai_verdict="BORDERLINE",
                admin_decision="CLEARED",
                admin_feedback="Solid fundamentals.",
                result_published_at=now,
            )
        ],
    )

    class _FakeService:
        async def get_recent_results(
            self, _user: SimpleNamespace, *, limit_per_type: int
        ) -> RecentResultsResponse:
            assert limit_per_type == 5
            return payload

    client.app.dependency_overrides[get_candidate_dashboard_service] = (
        lambda: _FakeService()
    )

    resp = client.get("/api/v1/candidate/recent-results")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["practice"]) == 1
    assert len(body["assigned"]) == 1
    assert body["practice"][0]["overall_score"] == "8.20"
    assert body["assigned"][0]["admin_decision"] == "CLEARED"
