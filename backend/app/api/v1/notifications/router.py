"""Notifications API — list the current user's notifications and unread count.

Available to any authenticated user (candidates and admins both need the
bell), so this uses ``get_current_user`` directly instead of
``require_roles(...)``. Every query is scoped to ``current_user.id`` — there
is no accepting-a-user-id-from-the-client anti-pattern here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.api.dependencies.database import get_db
from app.api.v1.notifications.schemas import (
    NotificationItem,
    NotificationListResponse,
)
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationListResponse:
    """List recent notifications for the current user."""
    repo = NotificationRepository(db)
    items = await repo.list_for_user(
        current_user.id, unread_only=unread_only, limit=limit
    )
    unread_count = await repo.count_unread(current_user.id)
    return NotificationListResponse(
        items=[NotificationItem.model_validate(item) for item in items],
        unread_count=unread_count,
    )
