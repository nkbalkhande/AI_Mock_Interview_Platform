"""Interview access-window logic.

An assigned interview is only startable inside an explicit time window
(``access_start_at`` .. ``access_end_at``). This module owns that rule so
routes/services never reimplement it inline. Missing bounds are treated
permissively (unbounded on that side), which matches the CHECK constraint's
allowance of NULLs.

States surfaced to the client:

- ``PENDING``  — before ``access_start_at``. Show "Scheduled", disable Join.
- ``OPEN``     — inside the window. Show "Join Interview".
- ``CLOSED``   — after ``access_end_at``. Show "Closed"; candidate missed it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from app.models.interview import Interview


class AccessState(StrEnum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def is_accessible(interview: Interview, *, now: datetime | None = None) -> bool:
    """Return ``True`` iff the interview is currently inside its access window."""
    return access_state(interview, now=now) is AccessState.OPEN


def access_state(
    interview: Interview, *, now: datetime | None = None
) -> AccessState:
    reference = now or _now()
    start = interview.access_start_at
    end = interview.access_end_at

    if start is not None and reference < start:
        return AccessState.PENDING
    if end is not None and reference > end:
        return AccessState.CLOSED
    return AccessState.OPEN
