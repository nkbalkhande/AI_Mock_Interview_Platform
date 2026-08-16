"""Repository for ``email_verifications``."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_verification import EmailVerification
from app.repositories.base import BaseRepository


def _normalize_email(email: str) -> str:
    return email.strip().lower()


class EmailVerificationRepository(BaseRepository[EmailVerification]):
    model = EmailVerification

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    async def get_latest(self, email: str) -> EmailVerification | None:
        """Most recent OTP row for ``email`` (any status)."""
        stmt = (
            select(EmailVerification)
            .where(func.lower(EmailVerification.email) == _normalize_email(email))
            .order_by(EmailVerification.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_verified_unconsumed(
        self, email: str
    ) -> EmailVerification | None:
        """Latest successful verification that has not been used to register."""
        stmt = (
            select(EmailVerification)
            .where(
                func.lower(EmailVerification.email) == _normalize_email(email),
                EmailVerification.verified_at.is_not(None),
                EmailVerification.consumed_at.is_(None),
            )
            .order_by(EmailVerification.verified_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_created_since(self, email: str, since: datetime) -> int:
        stmt = select(func.count()).select_from(EmailVerification).where(
            func.lower(EmailVerification.email) == _normalize_email(email),
            EmailVerification.created_at >= since,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def invalidate_open(self, email: str) -> None:
        """Expire unused OTPs so a newly issued code is the only valid one."""
        now = datetime.now(timezone.utc)
        await self.session.execute(
            update(EmailVerification)
            .where(
                func.lower(EmailVerification.email) == _normalize_email(email),
                EmailVerification.verified_at.is_(None),
                EmailVerification.consumed_at.is_(None),
            )
            .values(expires_at=now)
        )

    async def create_challenge(
        self,
        *,
        email: str,
        otp_hash: str,
        expires_at: datetime,
    ) -> EmailVerification:
        row = EmailVerification(
            email=_normalize_email(email),
            otp_hash=otp_hash,
            expires_at=expires_at,
            attempts=0,
        )
        return await self.add(row)
