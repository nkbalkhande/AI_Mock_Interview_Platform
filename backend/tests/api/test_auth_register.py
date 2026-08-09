"""API tests for POST /api/v1/auth/register.

The AuthService and FileStorageService are overridden with fakes so these run
fully offline — no database, engine connection, or disk writes needed.
Registration is multipart/form-data (it carries a resume upload).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.storage import get_storage_service
from app.api.v1.auth.router import get_auth_service
from app.core.exceptions import AlreadyExistsError
from app.main import create_app
from app.services.auth.auth_service import AuthenticatedUser
from app.services.auth.token_service import IssuedTokens
from app.services.storage.file_storage import StoredFile


def _fake_authenticated_user(email: str, full_name: str) -> AuthenticatedUser:
    now = datetime.now(timezone.utc)
    user = SimpleNamespace(
        id=uuid.uuid4(),
        full_name=full_name,
        email=email,
        user_roles=[SimpleNamespace(role=SimpleNamespace(name="CANDIDATE"))],
    )
    tokens = IssuedTokens(
        access_token="access.jwt.token",
        access_expires_at=now + timedelta(minutes=30),
        refresh_token="opaque-refresh",
        refresh_expires_at=now + timedelta(days=7),
    )
    return AuthenticatedUser(user=user, tokens=tokens)  # type: ignore[arg-type]


class _FakeStorage:
    """In-memory stand-in that never touches disk."""

    def save(
        self, *, category: str, original_name: str, data: bytes, content_type: str
    ) -> StoredFile:
        return StoredFile(
            file_name=original_name,
            file_path=f"{category}/{uuid.uuid4().hex}",
            content_type=content_type,
            size_bytes=len(data),
        )

    def delete(self, file_path: str) -> None:  # noqa: D401 - no-op cleanup
        return None


def _valid_form() -> dict[str, str]:
    return {
        "full_name": "Grace Hopper",
        "email": "grace@example.com",
        "password": "supersecret",
        "current_organization": "US Navy",
        "current_designation": "Rear Admiral",
        "years_of_experience": "40",
        "phone_number": "+1-202-555-0100",
    }


def _resume_file() -> dict[str, tuple[str, bytes, str]]:
    return {"resume": ("cv.pdf", b"%PDF-1.4 fake resume", "application/pdf")}


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    with TestClient(app) as c:
        c.app.dependency_overrides[get_storage_service] = lambda: _FakeStorage()
        yield c
    app.dependency_overrides.clear()


def test_register_success_creates_user_and_sets_cookies(client: TestClient) -> None:
    class _FakeService:
        async def register(
            self, *, full_name: str, email: str, **_: object
        ) -> AuthenticatedUser:
            return _fake_authenticated_user(email=email, full_name=full_name)

    client.app.dependency_overrides[get_auth_service] = lambda: _FakeService()

    resp = client.post(
        "/api/v1/auth/register", data=_valid_form(), files=_resume_file()
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["user"]["email"] == "grace@example.com"
    assert body["user"]["full_name"] == "Grace Hopper"
    assert body["user"]["roles"] == ["CANDIDATE"]
    assert "access_token" not in body
    assert "session" in resp.cookies
    assert "refresh_token" in resp.cookies


def test_register_success_with_binary_profile_photo(client: TestClient) -> None:
    """A binary (non-UTF-8) photo must not crash multipart parsing/validation."""

    class _FakeService:
        async def register(
            self, *, full_name: str, email: str, **_: object
        ) -> AuthenticatedUser:
            return _fake_authenticated_user(email=email, full_name=full_name)

    client.app.dependency_overrides[get_auth_service] = lambda: _FakeService()

    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR\x9c\x00\x00\x9c"
    files = _resume_file() | {
        "profile_photo": ("avatar.png", png_bytes, "image/png"),
    }

    resp = client.post("/api/v1/auth/register", data=_valid_form(), files=files)

    assert resp.status_code == 201
    assert resp.json()["user"]["email"] == "grace@example.com"


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    class _ConflictingService:
        async def register(self, **_: object) -> AuthenticatedUser:
            raise AlreadyExistsError("An account with this email already exists.")

    client.app.dependency_overrides[get_auth_service] = lambda: _ConflictingService()

    resp = client.post(
        "/api/v1/auth/register", data=_valid_form(), files=_resume_file()
    )

    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "already_exists"


def test_register_rejects_short_password(client: TestClient) -> None:
    form = _valid_form() | {"password": "short"}
    resp = client.post("/api/v1/auth/register", data=form, files=_resume_file())
    assert resp.status_code == 422


def test_register_rejects_malformed_email(client: TestClient) -> None:
    form = _valid_form() | {"email": "not-an-email"}
    resp = client.post("/api/v1/auth/register", data=form, files=_resume_file())
    assert resp.status_code == 422


def test_register_rejects_unsupported_resume_type(client: TestClient) -> None:
    bad_file = {"resume": ("cv.csv", b"a,b,c", "text/csv")}
    resp = client.post("/api/v1/auth/register", data=_valid_form(), files=bad_file)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_register_requires_resume_file(client: TestClient) -> None:
    resp = client.post("/api/v1/auth/register", data=_valid_form())
    assert resp.status_code == 422
