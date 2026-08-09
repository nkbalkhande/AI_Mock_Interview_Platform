"""Candidate-facing API routes.

Every route in this module is gated by ``require_roles(RoleName.CANDIDATE)``,
so an admin/interviewer token can't hit these endpoints — that keeps the
"candidate space" cleanly separated from admin tooling. The authenticated
user's id is always derived from the token; the frontend never sends a
``candidate_id`` (which would be a straightforward IDOR).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.api.dependencies.database import get_db
from app.api.v1.candidate.schemas import (
    DashboardResponse,
    RecentResultsResponse,
    UpcomingInterviewsResponse,
)
from app.api.v1.candidate.service import CandidateDashboardService
from app.domain.enums import RoleName
from app.models.user import User

router = APIRouter()


def get_candidate_dashboard_service(
    db: AsyncSession = Depends(get_db),
) -> CandidateDashboardService:
    return CandidateDashboardService(db)


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> DashboardResponse:
    """Return the candidate's dashboard overview (profile summary + stats)."""
    return await service.get_dashboard(current_user)


@router.get("/upcoming-interviews", response_model=UpcomingInterviewsResponse)
async def get_upcoming_interviews(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> UpcomingInterviewsResponse:
    """List the candidate's upcoming assigned interviews (soonest first)."""
    return await service.get_upcoming_interviews(current_user, limit=limit)


@router.get("/recent-results", response_model=RecentResultsResponse)
async def get_recent_results(
    limit_per_type: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> RecentResultsResponse:
    """Return the candidate's most recent completed interviews, split by type."""
    return await service.get_recent_results(current_user, limit_per_type=limit_per_type)
