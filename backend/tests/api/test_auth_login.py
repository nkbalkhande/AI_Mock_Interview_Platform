"""API tests for POST /api/v1/auth/login.

The AuthService is overridden with a fake so these run fully offline (no
database or engine connection needed).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.v1.auth.router import get_auth_service
from app.core.exceptions import AuthenticationError
from app.main import create_app
from app.services.auth.auth_service import AuthenticatedUser
from app.services.auth.token_service import IssuedTokens


def _fake_authenticated_user() -> AuthenticatedUser:
    now = datetime.now(timezone.utc)
    user = SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Ada Lovelace",
        email="ada@example.com",
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="CANDIDATE"))],
    )
    tokens = IssuedTokens(
        access_token="access.jwt.token",
        access_expires_at=now + timedelta(minutes=30),
        refresh_token="opaque-refresh",
        refresh_expires_at=now + timedelta(days=7),
    )
    return AuthenticatedUser(user=user, tokens=tokens)  # type: ignore[arg-type]


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_login_success_returns_user_and_sets_cookies(client: TestClient) -> None:
    class _FakeService:
        async def login(self, **_: object) -> AuthenticatedUser:
            return _fake_authenticated_user()

    client.app.dependency_overrides[get_auth_service] = lambda: _FakeService()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "whatever"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["email"] == "ada@example.com"
    assert body["user"]["roles"] == ["CANDIDATE"]
    # Tokens must be delivered via httpOnly cookies, never in the body.
    assert "access_token" not in body
    assert "session" in resp.cookies
    assert "refresh_token" in resp.cookies


def test_login_invalid_credentials_returns_401(client: TestClient) -> None:
    class _FailingService:
        async def login(self, **_: object) -> AuthenticatedUser:
            raise AuthenticationError("Invalid email or password.")

    client.app.dependency_overrides[get_auth_service] = lambda: _FailingService()

    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "ada@example.com", "password": "bad"},
    )

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_error"


def test_login_rejects_malformed_email(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "x"},
    )
    assert resp.status_code == 422
