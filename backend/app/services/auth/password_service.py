"""Password hashing/verification service.

A thin domain-facing wrapper over ``app.core.security`` so business code depends
on a service abstraction rather than the crypto primitives directly.
"""

from __future__ import annotations

from app.core.security import hash_password, verify_password


class PasswordService:
    def hash(self, plain_password: str) -> str:
        return hash_password(plain_password)

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return verify_password(plain_password, password_hash)
