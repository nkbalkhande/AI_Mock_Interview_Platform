"""Unit tests for PasswordService (no DB required)."""

from __future__ import annotations

from app.services.auth.password_service import PasswordService


def test_hash_then_verify() -> None:
    svc = PasswordService()
    hashed = svc.hash("hunter2")
    assert svc.verify("hunter2", hashed) is True
    assert svc.verify("nope", hashed) is False
