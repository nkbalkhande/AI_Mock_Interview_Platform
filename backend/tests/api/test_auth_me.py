"""API tests for GET /api/v1/auth/me + POST /api/v1/auth/logout.

The auth dependency is overridden with a fake so these run fully offline
(no DB, no JWT signing) — same pattern as the login/register tests.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.auth import get_current_user
from app.core.exceptions import AuthenticationError
from app.main import create_app


def _fake_user(*, roles: tuple[str, ...] = ("CANDIDATE",)) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        full_name="Ada Lovelace",
        email="ada@example.com",
        is_active=True,
        user_roles=[
            SimpleNamespace(role=SimpleNamespace(name=name)) for name in roles
        ],
    )


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_me_returns_current_user(client: TestClient) -> None:
    user = _fake_user()
    client.app.dependency_overrides[get_current_user] = lambda: user

    resp = client.get("/api/v1/auth/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "ada@example.com"
    assert body["roles"] == ["CANDIDATE"]
    assert body["id"] == str(user.id)


def test_me_returns_401_when_unauthenticated(client: TestClient) -> None:
    def _raise() -> SimpleNamespace:
        raise AuthenticationError("Session is invalid or expired.")

    client.app.dependency_overrides[get_current_user] = _raise

    resp = client.get("/api/v1/auth/me")

    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "authentication_error"


def test_logout_clears_auth_cookies(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/logout")

    assert resp.status_code == 204
    # Cookie deletion is expressed via Set-Cookie with Max-Age=0.
    set_cookie_headers = resp.headers.get_list("set-cookie")
    joined = " | ".join(set_cookie_headers)
    assert "session=" in joined
    assert "refresh_token=" in joined
    assert "Max-Age=0" in joined or 'Max-Age="0"' in joined or "max-age=0" in joined.lower()
