"""Authentication + RBAC FastAPI dependencies.

Route handlers depend on these instead of parsing cookies/tokens themselves so
auth logic stays in one place. Resolution order matches how the frontend sends
credentials: httpOnly ``session`` cookie first (browser flow), then
``Authorization: Bearer <token>`` (server-to-server / test clients).

``require_roles(*roles)`` returns a dependency callable so a route can gate on
one or more roles with the FastAPI ``Depends(...)`` idiom, e.g.::

    @router.get("/candidate/dashboard")
    async def dashboard(user: User = Depends(require_roles(RoleName.CANDIDATE))):
        ...
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.database import get_db
from app.core.constants import AUTH_HEADER_PREFIX
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.domain.enums import RoleName
from app.models.user import User
from app.repositories.user_repository import UserRepository

# Kept in sync with the cookie set by ``app.api.v1.auth.router``. If that name
# ever changes, both places must move together — colocating a constant here
# means the auth dependency never has to import the router module (avoids a
# circular import between routers and this shared dependency).
ACCESS_COOKIE_NAME = "session"  # noqa: S105 - cookie name, not a secret


def _extract_token(request: Request) -> str:
    cookie_token = request.cookies.get(ACCESS_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    header = request.headers.get("authorization")
    if header:
        scheme, _, value = header.partition(" ")
        if scheme.lower() == AUTH_HEADER_PREFIX.lower() and value:
            return value.strip()

    raise AuthenticationError("Authentication is required to access this resource.")


def _decode_access_claims(token: str) -> dict[str, Any]:
    try:
        claims = decode_token(token)
    except jwt.PyJWTError as exc:  # includes ExpiredSignatureError etc.
        raise AuthenticationError("Session is invalid or expired.") from exc

    if claims.get("type") != ACCESS_TOKEN_TYPE:
        # Prevents a stolen refresh token (or any non-access JWT that decodes)
        # from being used to hit protected endpoints.
        raise AuthenticationError("Session is invalid or expired.")
    return claims


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the request.

    Raises ``AuthenticationError`` (401) when no valid session is present,
    the JWT can't be decoded, or the referenced user no longer exists / is
    inactive. Returns a ``User`` with ``user_roles.role`` eager-loaded so
    downstream RBAC checks don't trigger extra queries.
    """
    token = _extract_token(request)
    claims = _decode_access_claims(token)

    subject = claims.get("sub")
    if not isinstance(subject, str):
        raise AuthenticationError("Session is invalid or expired.")

    try:
        user_id = uuid.UUID(subject)
    except ValueError as exc:
        raise AuthenticationError("Session is invalid or expired.") from exc

    users = UserRepository(db)
    user = await users.get_by_id_with_roles(user_id, with_profile=True)
    if user is None or not user.is_active:
        raise AuthenticationError("Session is invalid or expired.")
    return user


UserDependency = Callable[..., Coroutine[Any, Any, User]]


def require_roles(*allowed: RoleName) -> UserDependency:
    """Return a ``Depends``-able that ensures the current user has one of ``allowed``.

    A user with any elevated role passes an ``ADMIN``-guarded route etc.;
    intersect at the RBAC layer (not the DB) so future role additions don't
    require query changes.
    """
    allowed_names = {role.value for role in allowed}

    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        user_roles = {
            ur.role.name for ur in current_user.user_roles if ur.role is not None
        }
        if user_roles.isdisjoint(allowed_names):
            raise PermissionDeniedError(
                "You do not have permission to access this resource."
            )
        return current_user

    return _dependency
