"""Unit tests for EmailVerificationService (no Resend, no DB engine)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.exceptions import BusinessRuleError, RateLimitError
from app.core.security import generate_email_otp, hash_otp, verify_otp
from app.services.auth.email_verification_service import EmailVerificationService


class _FakeSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_verification_otp(self, *, to: str, otp: str) -> None:
        self.sent.append((to, otp))


class _FakeUserRepo:
    def __init__(self, existing: object | None = None) -> None:
        self.existing = existing

    async def get_by_email(self, email: str) -> object | None:
        return self.existing


class _FakeChallengeRepo:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    async def get_latest(self, email: str) -> Any | None:
        matches = [r for r in self.rows if r.email == email.strip().lower()]
        return matches[-1] if matches else None

    async def get_latest_verified_unconsumed(self, email: str) -> Any | None:
        matches = [
            r
            for r in self.rows
            if r.email == email.strip().lower()
            and r.verified_at is not None
            and r.consumed_at is None
        ]
        return matches[-1] if matches else None

    async def count_created_since(self, email: str, since: datetime) -> int:
        return sum(
            1
            for r in self.rows
            if r.email == email.strip().lower() and r.created_at >= since
        )

    async def invalidate_open(self, email: str) -> None:
        now = datetime.now(timezone.utc)
        for row in self.rows:
            if (
                row.email == email.strip().lower()
                and row.verified_at is None
                and row.consumed_at is None
            ):
                row.expires_at = now

    async def create_challenge(
        self, *, email: str, otp_hash: str, expires_at: datetime
    ) -> Any:
        row = SimpleNamespace(
            email=email.strip().lower(),
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
            created_at=datetime.now(timezone.utc),
            verified_at=None,
            consumed_at=None,
        )
        self.rows.append(row)
        return row


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


def _service(
    *,
    existing_user: object | None = None,
) -> tuple[EmailVerificationService, _FakeChallengeRepo, _FakeSender]:
    session = _FakeSession()
    service = EmailVerificationService(session, sender=_FakeSender())  # type: ignore[arg-type]
    challenges = _FakeChallengeRepo()
    sender = _FakeSender()
    service.challenges = challenges  # type: ignore[assignment]
    service.users = _FakeUserRepo(existing_user)  # type: ignore[assignment]
    service.sender = sender
    return service, challenges, sender


def test_hash_otp_is_not_plaintext() -> None:
    digest = hash_otp("a@b.com", "123456")
    assert digest != "123456"
    assert len(digest) == 64
    assert verify_otp("a@b.com", "123456", digest)
    assert not verify_otp("a@b.com", "000000", digest)
    assert not verify_otp("other@b.com", "123456", digest)


def test_generate_email_otp_is_six_digits() -> None:
    otp = generate_email_otp()
    assert len(otp) == 6
    assert otp.isdigit()


@pytest.mark.asyncio
async def test_send_otp_emails_hashed_code() -> None:
    service, challenges, sender = _service()
    result = await service.send_otp("Candidate@Example.com")
    assert result["success"] is True
    assert len(sender.sent) == 1
    to, otp = sender.sent[0]
    assert to == "candidate@example.com"
    assert otp.isdigit()
    assert challenges.rows[0].otp_hash != otp
    assert verify_otp(to, otp, challenges.rows[0].otp_hash)


@pytest.mark.asyncio
async def test_send_otp_enforces_cooldown() -> None:
    service, challenges, _sender = _service()
    await service.send_otp("a@b.com")
    with pytest.raises(RateLimitError) as exc:
        await service.send_otp("a@b.com")
    assert "Resend OTP" in exc.value.message
    assert challenges.rows  # first send kept


@pytest.mark.asyncio
async def test_verify_otp_success_and_consume() -> None:
    service, challenges, sender = _service()
    await service.send_otp("a@b.com")
    otp = sender.sent[0][1]
    result = await service.verify_otp("a@b.com", otp)
    assert result["verified"] is True
    consumed = await service.consume_verified("a@b.com")
    assert consumed.consumed_at is not None


@pytest.mark.asyncio
async def test_verify_otp_rejects_wrong_code_then_locks() -> None:
    service, _challenges, sender = _service()
    await service.send_otp("a@b.com")
    for _ in range(4):
        with pytest.raises(BusinessRuleError) as exc:
            await service.verify_otp("a@b.com", "000000")
        assert "Invalid verification code" in exc.value.message
    with pytest.raises(BusinessRuleError) as exc:
        await service.verify_otp("a@b.com", "000000")
    assert "Too many incorrect attempts" in exc.value.message
    # Even the real OTP is rejected after lockout.
    with pytest.raises(BusinessRuleError):
        await service.verify_otp("a@b.com", sender.sent[0][1])


@pytest.mark.asyncio
async def test_expired_otp_cannot_be_used() -> None:
    service, challenges, sender = _service()
    await service.send_otp("a@b.com")
    challenges.rows[0].expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with pytest.raises(BusinessRuleError) as exc:
        await service.verify_otp("a@b.com", sender.sent[0][1])
    assert "expired" in exc.value.message.lower()


@pytest.mark.asyncio
async def test_new_otp_invalidates_previous_verification() -> None:
    service, challenges, sender = _service()
    await service.send_otp("a@b.com")
    await service.verify_otp("a@b.com", sender.sent[0][1])
    # Bypass cooldown for the follow-up send.
    challenges.rows[0].created_at = datetime.now(timezone.utc) - timedelta(minutes=2)
    await service.send_otp("a@b.com")
    with pytest.raises(BusinessRuleError) as exc:
        await service.consume_verified("a@b.com")
    assert "Email verification is required" in exc.value.message


@pytest.mark.asyncio
async def test_register_requires_verification() -> None:
    service, _challenges, _sender = _service()
    with pytest.raises(BusinessRuleError) as exc:
        await service.consume_verified("nobody@example.com")
    assert exc.value.message == "Email verification is required before registration."
