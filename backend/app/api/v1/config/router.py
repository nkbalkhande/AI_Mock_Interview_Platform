"""Public, non-secret config for the frontend.

Values come from ``settings/config.yaml`` so interview limits and duration
options stay in lockstep with backend validation.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/public")
async def get_public_config() -> dict:
    return settings.public_config()
