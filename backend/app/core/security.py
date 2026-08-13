"""Security primitives: password hashing and JWT handling.

Kept framework-agnostic and dependency-light so services can compose these
without importing FastAPI. Password hashing uses bcrypt via passlib; JWTs use
PyJWT and are signed with the symmetric ``JWT_SECRET_KEY``.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt only considers the first 72 bytes of a password and raises on longer
# inputs; we truncate defensively so hashing/verification never blow up.
_BCRYPT_MAX_BYTES = 72

# JWT ``type`` claim values so an access token can never be used as a refresh
# token (or vice-versa) even if it validates structurally.
ACCESS_TOKEN_TYPE = "access"  # noqa: S105 - claim label, not a secret
REFRESH_TOKEN_TYPE = "refresh"  # noqa: S105 - claim label, not a secret


def _to_bcrypt_bytes(plain_password: str) -> bytes:
    return plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for ``plain_password``."""
    return bcrypt.hashpw(_to_bcrypt_bytes(plain_password), bcrypt.gensalt()).decode(
        "utf-8"
    )


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return ``True`` if ``plain_password`` matches the stored hash.

    Never raises on malformed hashes — returns ``False`` instead so callers can
    treat "bad password" and "corrupt hash" uniformly as an auth failure.
    """
    try:
        return bcrypt.checkpw(
            _to_bcrypt_bytes(plain_password), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    subject: str,
    *,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """Create a signed access JWT for ``subject`` (the user id).

    Returns the encoded token and its absolute expiry so callers can align
    cookie ``max-age`` with the token lifetime.
    """
    expire_at = _now() + (
        expires_delta
        or timedelta(minutes=settings.auth.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "type": ACCESS_TOKEN_TYPE,
        "iat": _now(),
        "exp": expire_at,
    }
    if extra_claims:
        payload.update(extra_claims)
    token = jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.auth.jwt_algorithm
    )
    return token, expire_at


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT. Raises ``jwt.PyJWTError`` on any problem."""
    return jwt.decode(
        token, settings.JWT_SECRET_KEY, algorithms=[settings.auth.jwt_algorithm]
    )


def generate_refresh_token() -> str:
    """Generate a cryptographically-random opaque refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Deterministic SHA-256 hash used to store refresh tokens at rest.

    Refresh tokens are opaque random strings, so a fast one-way hash is
    sufficient (and lets us look tokens up by hash). Fits the ``varchar(128)``
    ``token_hash`` column.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
