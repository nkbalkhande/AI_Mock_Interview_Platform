"""Response schemas for the notifications API."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
    read_at: datetime | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    unread_count: int
