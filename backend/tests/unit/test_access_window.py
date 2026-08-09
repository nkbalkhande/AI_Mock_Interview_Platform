"""Unit tests for the interview access-window helper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.interviews.access_window import AccessState, access_state, is_accessible


def _interview(start_offset_min: int | None, end_offset_min: int | None) -> SimpleNamespace:
    now = datetime.now(timezone.utc)
    return SimpleNamespace(
        access_start_at=(
            now + timedelta(minutes=start_offset_min)
            if start_offset_min is not None
            else None
        ),
        access_end_at=(
            now + timedelta(minutes=end_offset_min)
            if end_offset_min is not None
            else None
        ),
    )


def test_pending_before_window() -> None:
    interview = _interview(start_offset_min=5, end_offset_min=30)
    assert access_state(interview) is AccessState.PENDING
    assert is_accessible(interview) is False


def test_open_inside_window() -> None:
    interview = _interview(start_offset_min=-5, end_offset_min=30)
    assert access_state(interview) is AccessState.OPEN
    assert is_accessible(interview) is True


def test_closed_after_window() -> None:
    interview = _interview(start_offset_min=-60, end_offset_min=-5)
    assert access_state(interview) is AccessState.CLOSED
    assert is_accessible(interview) is False


def test_null_bounds_are_permissive() -> None:
    interview = _interview(start_offset_min=None, end_offset_min=None)
    assert access_state(interview) is AccessState.OPEN
    assert is_accessible(interview) is True


def test_pending_when_only_start_and_before() -> None:
    interview = _interview(start_offset_min=15, end_offset_min=None)
    assert access_state(interview) is AccessState.PENDING


def test_closed_when_only_end_and_after() -> None:
    interview = _interview(start_offset_min=None, end_offset_min=-1)
    assert access_state(interview) is AccessState.CLOSED
