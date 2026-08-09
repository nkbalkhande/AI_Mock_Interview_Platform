"""API tests for GET /api/v1/notifications.

The database dependency is overridden with a fake ``AsyncSession`` that
short-circuits ``NotificationRepository`` execution — we can't easily fake
the repository directly because the router constructs it inline (mirroring
the auth router's local ``get_auth_service`` pattern is fine there because
that dep exists; here we override the repo through the session boundary).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.main import create_app


def _user() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Ada",
        email="ada@example.com",
        is_active=True,
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="CANDIDATE"))],
    )


class _FakeNotification:
    """Duck-typed enough for ``NotificationItem.model_validate``."""

    def __init__(self) -> None:
        self.id = uuid.uuid4()
        self.type = "INTERVIEW_ASSIGNED"
        self.title = "You have a new interview"
        self.message = "Please attend on Monday."
        self.is_read = False
        self.created_at = datetime.now(timezone.utc)
        self.read_at = None
        self.reference_type = "interview"
        self.reference_id = uuid.uuid4()


class _FakeSession:
    """Fake ``AsyncSession`` — ``NotificationRepository`` runs ``select`` +
    ``func.count`` statements through ``session.execute(...)``. We identify
    which query is being run by whether the compiled SQL selects ``count``.
    """

    def __init__(self, notifications: list[_FakeNotification], unread: int) -> None:
        self._notifications = notifications
        self._unread = unread

    async def execute(self, stmt: Any) -> Any:
        compiled = str(stmt).lower()
        if "count(" in compiled:
            return SimpleNamespace(scalar_one=lambda: self._unread)

        scalars_obj = SimpleNamespace(all=lambda: self._notifications)
        return SimpleNamespace(scalars=lambda: scalars_obj)


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_notifications_list_returns_items_and_unread_count(client: TestClient) -> None:
    user = _user()
    notifications = [_FakeNotification(), _FakeNotification()]
    session = _FakeSession(notifications=notifications, unread=2)

    client.app.dependency_overrides[get_current_user] = lambda: user

    async def _yield_session() -> Any:
        yield session

    client.app.dependency_overrides[get_db] = _yield_session

    resp = client.get("/api/v1/notifications")

    assert resp.status_code == 200
    body = resp.json()
    assert body["unread_count"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["type"] == "INTERVIEW_ASSIGNED"


def test_notifications_requires_authentication(client: TestClient) -> None:
    from app.core.exceptions import AuthenticationError

    def _raise() -> SimpleNamespace:
        raise AuthenticationError("Authentication is required.")

    client.app.dependency_overrides[get_current_user] = _raise

    resp = client.get("/api/v1/notifications")

    assert resp.status_code == 401
