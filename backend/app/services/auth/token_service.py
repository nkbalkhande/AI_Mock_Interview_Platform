"""Token issuance service.

Issues a short-lived access JWT plus an opaque refresh token. The refresh token
is returned to the caller in plaintext (to set as a cookie) but only its hash is
persisted in ``refresh_tokens`` — the raw value never touches the database.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)
from app.models.refresh_token import RefreshToken


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    access_expires_at: datetime
    refresh_token: str
    refresh_expires_at: datetime


class TokenService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def issue_for_user(
        self,
        user_id: uuid.UUID,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
    ) -> IssuedTokens:
        """Create an access + refresh token pair and persist the refresh row."""
        access_token, access_expires_at = create_access_token(str(user_id))

        refresh_token = generate_refresh_token()
        refresh_expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.auth.refresh_token_expire_days
        )

        self.session.add(
            RefreshToken(
                user_id=user_id,
                token_hash=hash_refresh_token(refresh_token),
                expires_at=refresh_expires_at,
                user_agent=user_agent,
                ip_address=ip_address,
            )
        )
        await self.session.flush()

        return IssuedTokens(
            access_token=access_token,
            access_expires_at=access_expires_at,
            refresh_token=refresh_token,
            refresh_expires_at=refresh_expires_at,
        )
