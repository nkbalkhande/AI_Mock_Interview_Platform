"""Top-level API router.

Aggregates all versioned domain routers under a single ``api_router`` that
``main.py`` mounts at ``settings.API_V1_PREFIX``. Domain routers are wired in
as each phase is implemented (auth, users, resumes, interviews, ...).
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth.router import router as auth_router
from app.api.v1.candidate.interview_router import router as candidate_interview_router
from app.api.v1.candidate.router import router as candidate_router
from app.api.v1.notifications.router import router as notifications_router

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

# Additional domain routers are included here as they come online
# (admin, interviews, ...).
