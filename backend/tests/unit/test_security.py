"""Unit tests for password hashing and JWT helpers (no DB required)."""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    ACCESS_TOKEN_TYPE,
    create_access_token,
    decode_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_hash_password_is_not_plaintext_and_verifies() -> None:
    hashed = hash_password("s3cret-pw")
    assert hashed != "s3cret-pw"
    assert verify_password("s3cret-pw", hashed) is True


def test_verify_password_rejects_wrong_password() -> None:
    hashed = hash_password("correct")
    assert verify_password("wrong", hashed) is False


def test_verify_password_handles_malformed_hash() -> None:
    assert verify_password("anything", "not-a-real-hash") is False


def test_access_token_round_trips_with_subject_and_type() -> None:
    token, expires_at = create_access_token("user-123")
    decoded = decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["type"] == ACCESS_TOKEN_TYPE
    assert expires_at is not None


def test_expired_access_token_is_rejected() -> None:
    token, _ = create_access_token("user-123", expires_delta=timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_refresh_tokens_are_unique_and_hash_is_stable() -> None:
    a = generate_refresh_token()
    b = generate_refresh_token()
    assert a != b
    assert hash_refresh_token(a) == hash_refresh_token(a)
    assert len(hash_refresh_token(a)) <= 128
