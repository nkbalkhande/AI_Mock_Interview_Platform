"""API tests for registration email OTP endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.v1.auth.router import get_email_verification_service
from app.core.exceptions import (
    AlreadyExistsError,
    BusinessRuleError,
    RateLimitError,
)
from app.main import create_app


class _FakeVerificationService:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.verified: dict[str, str] = {}

    async def send_otp(self, email: str) -> dict[str, object]:
        self.sent.append(email)
        return {
            "success": True,
            "message": "Verification OTP sent successfully.",
            "cooldown_seconds": 60,
        }

    async def verify_otp(self, email: str, otp: str) -> dict[str, object]:
        self.verified[email] = otp
        return {
            "success": True,
            "verified": True,
            "message": "Email verified successfully.",
        }


def _client(service: object | None = None) -> TestClient:
    app = create_app()
    fake = service or _FakeVerificationService()
    app.dependency_overrides[get_email_verification_service] = lambda: fake
    return TestClient(app)


def test_send_email_otp_success() -> None:
    fake = _FakeVerificationService()
    client = _client(fake)
    resp = client.post(
        "/api/v1/auth/send-email-otp", json={"email": "candidate@example.com"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["message"] == "Verification OTP sent successfully."
    assert fake.sent == ["candidate@example.com"]


def test_send_email_otp_rejects_invalid_email() -> None:
    resp = _client().post("/api/v1/auth/send-email-otp", json={"email": "not-an-email"})
    assert resp.status_code == 422


def test_send_email_otp_duplicate_account() -> None:
    class _Exists:
        async def send_otp(self, email: str) -> dict[str, object]:
            raise AlreadyExistsError("An account with this email already exists.")

    resp = _client(_Exists()).post(
        "/api/v1/auth/send-email-otp", json={"email": "taken@example.com"}
    )
    assert resp.status_code == 409


def test_send_email_otp_cooldown() -> None:
    class _Cooldown:
        async def send_otp(self, email: str) -> dict[str, object]:
            raise RateLimitError(
                "Resend OTP in 45 seconds", details={"retry_after_seconds": 45}
            )

    resp = _client(_Cooldown()).post(
        "/api/v1/auth/send-email-otp", json={"email": "candidate@example.com"}
    )
    assert resp.status_code == 429
    assert resp.json()["error"]["code"] == "rate_limited"


def test_verify_email_success() -> None:
    fake = _FakeVerificationService()
    resp = _client(fake).post(
        "/api/v1/auth/verify-email",
        json={"email": "candidate@example.com", "otp": "483921"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["verified"] is True
    assert fake.verified["candidate@example.com"] == "483921"


def test_verify_email_invalid_otp() -> None:
    class _Invalid:
        async def verify_otp(self, email: str, otp: str) -> dict[str, object]:
            raise BusinessRuleError(
                "Invalid verification code. Please enter the correct OTP."
            )

    resp = _client(_Invalid()).post(
        "/api/v1/auth/verify-email",
        json={"email": "candidate@example.com", "otp": "000000"},
    )
    assert resp.status_code == 400
    assert "Invalid verification code" in resp.json()["error"]["message"]


def test_verify_email_rejects_non_digit_otp() -> None:
    resp = _client().post(
        "/api/v1/auth/verify-email",
        json={"email": "candidate@example.com", "otp": "abcdef"},
    )
    assert resp.status_code == 422
