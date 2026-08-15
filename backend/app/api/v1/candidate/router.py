"""Candidate-facing API routes.

Every route in this module is gated by ``require_roles(RoleName.CANDIDATE)``,
so an admin/interviewer token can't hit these endpoints — that keeps the
"candidate space" cleanly separated from admin tooling. The authenticated
user's id is always derived from the token; the frontend never sends a
``candidate_id`` (which would be a straightforward IDOR).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.api.dependencies.database import get_db
from app.api.dependencies.storage import get_storage_service
from app.api.v1.candidate.schemas import (
    AssignedResultDetail,
    AssignedResultListResponse,
    CandidateProfileResponse,
    CandidateProfileUpdateRequest,
    DashboardResponse,
    InterviewHistoryResponse,
    PracticeResultListResponse,
    RecentResultsResponse,
    UpcomingInterviewDetail,
    UpcomingInterviewsResponse,
)
from app.api.v1.candidate.service import CandidateDashboardService
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.domain.enums import RoleName
from app.models.user import User
from app.services.storage.file_storage import FileStorageService

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


@router.get("/profile", response_model=CandidateProfileResponse)
async def get_profile(
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> CandidateProfileResponse:
    """Return the currently signed-in candidate's full profile."""
    return await service.get_profile(current_user)


@router.patch("/profile", response_model=CandidateProfileResponse)
async def update_profile(
    payload: CandidateProfileUpdateRequest,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> CandidateProfileResponse:
    """Update the authenticated candidate's profile."""
    return await service.update_profile(current_user, payload)


_PHOTO_CONTENT_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/jpg", "image/webp"}
)


@router.put("/profile/photo", response_model=CandidateProfileResponse)
async def upload_profile_photo(
    photo: UploadFile = File(...),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
    storage: FileStorageService = Depends(get_storage_service),
) -> CandidateProfileResponse:
    """Upload or replace the candidate's profile photo."""
    data = await photo.read()
    if not data:
        raise ValidationError("The photo file is empty.")

    max_bytes = settings.storage.max_upload_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise ValidationError(
            f"Photo exceeds the {settings.storage.max_upload_size_mb}MB limit."
        )

    content_type = (photo.content_type or "").lower()
    if content_type not in _PHOTO_CONTENT_TYPES:
        raise ValidationError(
            f"Unsupported photo type: {content_type or 'unknown'}. "
            "Use JPEG, PNG, or WebP."
        )

    old_path = (
        current_user.profile.profile_photo_path
        if current_user.profile
        else None
    )

    stored = storage.save(
        category="photos",
        original_name=photo.filename or "photo",
        data=data,
        content_type=content_type,
    )

    try:
        result = await service.update_profile_photo(current_user, stored.file_path)
    except Exception:
        storage.delete(stored.file_path)
        raise

    if old_path:
        storage.delete(old_path)

    return result


@router.get("/upcoming-interviews", response_model=UpcomingInterviewsResponse)
async def get_upcoming_interviews(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> UpcomingInterviewsResponse:
    """List the candidate's upcoming assigned interviews (soonest first)."""
    return await service.get_upcoming_interviews(current_user, limit=limit)


@router.get(
    "/upcoming-interviews/{interview_id}",
    response_model=UpcomingInterviewDetail,
)
async def get_upcoming_interview_detail(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> UpcomingInterviewDetail:
    """Get full details for a single assigned interview (pre-join view)."""
    result = await service.get_upcoming_interview_detail(current_user, interview_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return result


@router.get("/recent-results", response_model=RecentResultsResponse)
async def get_recent_results(
    limit_per_type: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> RecentResultsResponse:
    """Return the candidate's most recent completed interviews, split by type."""
    return await service.get_recent_results(current_user, limit_per_type=limit_per_type)


@router.get("/interviews/history", response_model=InterviewHistoryResponse)
async def get_interview_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    status_filter: str | None = Query(
        default=None,
        description="Filter: all | completed | in_progress | evaluating | incomplete",
    ),
    type_filter: str | None = Query(
        default=None, description="Filter: all | practice | assigned"
    ),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> InterviewHistoryResponse:
    """Full interview history — every interview the candidate started or was assigned."""
    return await service.get_interview_history(
        current_user,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        type_filter=type_filter,
    )


@router.get("/results/practice", response_model=PracticeResultListResponse)
async def get_practice_results(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> PracticeResultListResponse:
    """List all completed practice interview results (paginated)."""
    return await service.get_practice_results(
        current_user, page=page, page_size=page_size
    )


@router.get("/results/assigned", response_model=AssignedResultListResponse)
async def get_assigned_results(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> AssignedResultListResponse:
    """List all completed assigned interview results (paginated)."""
    return await service.get_assigned_results(
        current_user, page=page, page_size=page_size
    )


@router.get(
    "/results/assigned/{session_id}",
    response_model=AssignedResultDetail,
)
async def get_assigned_result_detail(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: CandidateDashboardService = Depends(get_candidate_dashboard_service),
) -> AssignedResultDetail:
    """Result for a single assigned interview session.

    Returns a ``PENDING_REVIEW`` shell (no AI scores/verdict) until the
    admin publishes a final decision.
    """
    result = await service.get_assigned_result_detail(current_user, session_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    return result
