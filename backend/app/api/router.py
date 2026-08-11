"""Top-level API router.

Aggregates all versioned domain routers under a single ``api_router`` that
``main.py`` mounts at ``settings.API_V1_PREFIX``. Domain routers are wired in
as each phase is implemented (auth, users, resumes, interviews, ...).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin.router import router as admin_router
from app.api.v1.auth.router import router as auth_router
from app.api.v1.candidate.interview_router import router as candidate_interview_router
from app.api.v1.candidate.router import router as candidate_router
from app.api.v1.files.router import router as files_router
from app.api.v1.notifications.router import router as notifications_router
from app.api.v1.voice.router import router as voice_router

api_router = APIRouter()


@api_router.get("/ping", tags=["health"])
async def ping() -> dict[str, str]:
    return {"status": "ok"}


api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(
    candidate_router, prefix="/candidate", tags=["candidate"]
)
api_router.include_router(
    candidate_interview_router,
    prefix="/candidate/interviews",
    tags=["candidate", "interviews"],
)
api_router.include_router(
    notifications_router, prefix="/notifications", tags=["notifications"]
)
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(files_router, prefix="/files", tags=["files"])
api_router.include_router(voice_router, prefix="/voice", tags=["voice"])
