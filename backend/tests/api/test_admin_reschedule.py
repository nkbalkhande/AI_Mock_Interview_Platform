from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.v1.admin.router import get_admin_service
from app.core.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    NotFoundError,
    ValidationError,
)
from app.main import create_app


def _admin() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Admin",
        email="admin@example.com",
        is_active=True,
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="ADMIN"))],
    )


def _candidate() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Ada",
        email="ada@example.com",
        is_active=True,
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="CANDIDATE"))],
    )


class _FakeAdminService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._returns: Any = None
        self._raises: Exception | None = None

    def configure(self, *, returns: Any = None, raises: Exception | None = None) -> None:
        self._returns = returns
        self._raises = raises

    async def reschedule_interview(self, interview_id, request, admin):  # noqa: ANN001
        self.calls.append(
            (
                "reschedule_interview",
                {
                    "interview_id": interview_id,
                    "request": request,
                    "admin_id": admin.id,
                },
            )
        )
        if self._raises is not None:
            raise self._raises
        return self._returns


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_reschedule_requires_authentication(client: TestClient) -> None:
    def _raise() -> SimpleNamespace:
        raise AuthenticationError("Authentication is required.")

    client.app.dependency_overrides[get_current_user] = _raise
    resp = client.patch(
        f"/api/v1/admin/interviews/{uuid.uuid4()}/reschedule",
        json={"new_scheduled_at": "2026-08-16T15:00:00+05:30"},
    )
    assert resp.status_code == 401


def test_reschedule_forbidden_for_candidate(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = _candidate
    resp = client.patch(
        f"/api/v1/admin/interviews/{uuid.uuid4()}/reschedule",
        json={"new_scheduled_at": "2026-08-16T15:00:00+05:30"},
    )
    assert resp.status_code == 403


def test_reschedule_happy_path(client: TestClient) -> None:
    admin = _admin()
    client.app.dependency_overrides[get_current_user] = lambda: admin
    fake = _FakeAdminService()
    interview_id = uuid.uuid4()
    scheduled = datetime(2026, 8, 16, 9, 30, tzinfo=timezone.utc)
    fake.configure(
        returns=SimpleNamespace(
            success=True,
            message="Interview rescheduled successfully",
            interview_id=interview_id,
            status="RESCHEDULED",
            scheduled_at=scheduled,
            original_scheduled_at=scheduled - timedelta(days=2),
            reschedule_count=1,
            notification_sent=True,
        )
    )
    client.app.dependency_overrides[get_admin_service] = lambda: fake

    resp = client.patch(
        f"/api/v1/admin/interviews/{interview_id}/reschedule",
        json={
            "new_scheduled_at": "2026-08-16T15:00:00+05:30",
            "reason": "Candidate missed scheduled interview",
            "notify_candidate": True,
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["status"] == "RESCHEDULED"
    assert body["reschedule_count"] == 1
    assert body["notification_sent"] is True
    assert fake.calls[0][1]["interview_id"] == interview_id
    assert fake.calls[0][1]["request"].reason == "Candidate missed scheduled interview"


def test_reschedule_not_found(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = _admin
    fake = _FakeAdminService()
    fake.configure(raises=NotFoundError("Interview not found."))
    client.app.dependency_overrides[get_admin_service] = lambda: fake

    resp = client.patch(
        f"/api/v1/admin/interviews/{uuid.uuid4()}/reschedule",
        json={"new_scheduled_at": "2026-08-16T15:00:00+05:30"},
    )
    assert resp.status_code == 404


def test_reschedule_rejects_non_missed(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = _admin
    fake = _FakeAdminService()
    fake.configure(
        raises=BusinessRuleError("Only missed interviews can be rescheduled.")
    )
    client.app.dependency_overrides[get_admin_service] = lambda: fake

    resp = client.patch(
        f"/api/v1/admin/interviews/{uuid.uuid4()}/reschedule",
        json={"new_scheduled_at": "2026-08-16T15:00:00+05:30"},
    )
    assert resp.status_code == 400
    assert "missed" in resp.json()["error"]["message"]


def test_reschedule_rejects_past_datetime(client: TestClient) -> None:
    client.app.dependency_overrides[get_current_user] = _admin
    fake = _FakeAdminService()
    fake.configure(
        raises=ValidationError("New interview date/time cannot be in the past.")
    )
    client.app.dependency_overrides[get_admin_service] = lambda: fake

    resp = client.patch(
        f"/api/v1/admin/interviews/{uuid.uuid4()}/reschedule",
        json={"new_scheduled_at": "2020-01-01T10:00:00+00:00"},
    )
    assert resp.status_code == 422
