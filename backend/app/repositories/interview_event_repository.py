"""Repository for ``interview_events``.

The events table is append-only; this repo intentionally exposes no update or
delete API. Every lifecycle-changing action in the interview flow should
record an event via ``record(...)`` so the audit trail stays complete.
"""

from __future__ import annotations

import uuid

from app.models.interview_event import InterviewEvent
from app.repositories.base import BaseRepository


class InterviewEventRepository(BaseRepository[InterviewEvent]):
    model = InterviewEvent

    async def record(
        self,
        *,
        interview_id: uuid.UUID,
        session_id: uuid.UUID | None,
        event_type: str,
        actor_user_id: uuid.UUID | None,
        metadata: dict | None = None,
    ) -> InterviewEvent:
        """Persist an event. ``metadata`` is stored under the DB column
        ``metadata`` (aliased to the ORM attr ``meta``)."""
        event = InterviewEvent(
            interview_id=interview_id,
            session_id=session_id,
            event_type=event_type,
            actor_user_id=actor_user_id,
            meta=metadata or {},
        )
        self.session.add(event)
        await self.session.flush()
        return event
