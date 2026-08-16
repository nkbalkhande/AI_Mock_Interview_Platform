"""Registration email OTP: issue, verify, and consume a hashed challenge."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    BusinessRuleError,
    RateLimitError,
    ValidationError,
)
from app.core.security import generate_email_otp, hash_otp, verify_otp
from app.models.email_verification import EmailVerification
from app.repositories.email_verification_repository import (
    EmailVerificationRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.email.brevo_sender import BrevoEmailSender, EmailSender

_OTP_RE = re.compile(r"^\d{6}$")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class EmailVerificationService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        sender: EmailSender | None = None,
    ) -> None:
        self.session = session
        self.challenges = EmailVerificationRepository(session)
        self.users = UserRepository(session)
        self.sender = sender or BrevoEmailSender()

    async def send_otp(self, email: str) -> dict[str, object]:
        """Create a new hashed OTP, invalidate prior unused codes, and email it."""
        email = _normalize_email(email)
        cfg = settings.email_verification

        existing_user = await self.users.get_by_email(email)
        if existing_user is not None:
            raise AlreadyExistsError("An account with this email already exists.")

        latest = await self.challenges.get_latest(email)
        if latest is not None:
            elapsed = (_now() - latest.created_at).total_seconds()
            remaining = cfg.resend_cooldown_seconds - int(elapsed)
            if remaining > 0:
                raise RateLimitError(
                    f"Resend OTP in {remaining} seconds",
                    details={"retry_after_seconds": remaining},
                )

        hour_ago = _now() - timedelta(hours=1)
        sent_last_hour = await self.challenges.count_created_since(email, hour_ago)
        if sent_last_hour >= cfg.max_sends_per_hour:
            raise RateLimitError(
                "Too many verification emails. Please try again later.",
                details={"retry_after_seconds": 3600},
            )

        otp = generate_email_otp()
        await self.challenges.invalidate_open(email)
        await self.challenges.create_challenge(
            email=email,
            otp_hash=hash_otp(email, otp),
            expires_at=_now() + timedelta(minutes=cfg.otp_ttl_minutes),
        )
        self.sender.send_verification_otp(to=email, otp=otp)
        await self.session.commit()
        return {
            "success": True,
            "message": "Verification OTP sent successfully.",
            "cooldown_seconds": cfg.resend_cooldown_seconds,
        }

    async def verify_otp(self, email: str, otp: str) -> dict[str, object]:
        """Mark the latest challenge verified if the OTP is valid and unexpired."""
        email = _normalize_email(email)
        otp = (otp or "").strip()
        if not _OTP_RE.match(otp):
            raise ValidationError("Enter the 6-digit verification code.")

        challenge = await self.challenges.get_latest(email)
        if challenge is None:
            raise BusinessRuleError(
                "No verification code found. Please request a new OTP."
            )
        if challenge.consumed_at is not None:
            raise BusinessRuleError(
                "This email has already been used to create an account."
            )
        if challenge.verified_at is not None:
            return {
                "success": True,
                "verified": True,
                "message": "Email verified successfully.",
            }

        cfg = settings.email_verification
        if challenge.attempts >= cfg.max_attempts:
            raise BusinessRuleError(
                "Too many incorrect attempts. Please request a new OTP."
            )
        if challenge.expires_at <= _now():
            raise BusinessRuleError(
                "This verification code has expired. Please request a new OTP."
            )
        if not verify_otp(email, otp, challenge.otp_hash):
            challenge.attempts += 1
            await self.session.commit()
            if challenge.attempts >= cfg.max_attempts:
                raise BusinessRuleError(
                    "Too many incorrect attempts. Please request a new OTP."
                )
            raise BusinessRuleError(
                "Invalid verification code. Please enter the correct OTP."
            )

        challenge.verified_at = _now()
        await self.session.commit()
        return {
            "success": True,
            "verified": True,
            "message": "Email verified successfully.",
        }

    async def consume_verified(self, email: str) -> EmailVerification:
        """Require the latest OTP for ``email`` to be verified and unused.

        A newer send invalidates a previous verification. Does not commit —
        the caller (registration) owns the transaction.
        """
        challenge = await self.challenges.get_latest(email)
        if (
            challenge is None
            or challenge.verified_at is None
            or challenge.consumed_at is not None
        ):
            raise BusinessRuleError(
                "Email verification is required before registration."
            )
        challenge.consumed_at = _now()
        return challenge
