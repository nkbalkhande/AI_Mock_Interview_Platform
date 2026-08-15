"""Admin-facing API routes.

Every route is gated by ``require_roles(RoleName.ADMIN)`` so only admin users
can access these endpoints.  The authenticated admin's id is derived from the
token for audit trail purposes.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_roles
from app.api.dependencies.database import get_db
from app.api.v1.admin.schemas import (
    AdminDashboardResponse,
    AssignInterviewRequest,
    AssignInterviewResponse,
    EvaluationDetailResponse,
    EvaluationListResponse,
    InterviewDetailResponse,
    InterviewListResponse,
    RescheduleInterviewRequest,
    RescheduleInterviewResponse,
    JobRoleItem,
    SubmitDecisionRequest,
    SubmitDecisionResponse,
    UpdateUserStatusRequest,
    UpdateUserStatusResponse,
    UserDetailResponse,
    UserListResponse,
)
from app.api.v1.admin.service import AdminService
from app.domain.enums import RoleName
from app.models.user import User

router = APIRouter()


def get_admin_service(
    db: AsyncSession = Depends(get_db),
) -> AdminService:
    return AdminService(db)


# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def get_dashboard(
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> AdminDashboardResponse:
    """Return the admin dashboard overview with stats and recent activity."""
    return await service.get_dashboard()


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------


@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> UserListResponse:
    """Paginated user list with optional search/filter."""
    return await service.list_users(
        page=page,
        page_size=page_size,
        search=search,
        role=role,
        is_active=is_active,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> UserDetailResponse:
    """Full user detail including profile and interview history."""
    result = await service.get_user_detail(
        user_id, page=page, page_size=page_size
    )
    if result is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return result


@router.patch(
    "/users/{user_id}/status", response_model=UpdateUserStatusResponse
)
async def update_user_status(
    user_id: uuid.UUID,
    request: UpdateUserStatusRequest,
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> UpdateUserStatusResponse:
    """Activate or deactivate a user account."""
    result = await service.update_user_status(user_id, request)
    if result is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return result


# ------------------------------------------------------------------
# Interviews
# ------------------------------------------------------------------


@router.get("/interviews", response_model=InterviewListResponse)
async def list_interviews(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    interview_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> InterviewListResponse:
    """Paginated list of all interviews with optional filters."""
    return await service.list_interviews(
        page=page,
        page_size=page_size,
        status=status,
        interview_type=interview_type,
        search=search,
    )


@router.get(
    "/interviews/{interview_id}", response_model=InterviewDetailResponse
)
async def get_interview_detail(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> InterviewDetailResponse:
    """Get full details for a single interview."""
    result = await service.get_interview_detail(interview_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return result


@router.post("/interviews/assign", response_model=AssignInterviewResponse)
async def assign_interview(
    request: AssignInterviewRequest,
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> AssignInterviewResponse:
    """Assign a new interview to a candidate."""
    try:
        return await service.assign_interview(request, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch(
    "/interviews/{interview_id}/cancel",
    response_model=InterviewDetailResponse,
)
async def cancel_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> InterviewDetailResponse:
    """Cancel an interview."""
    result = await service.cancel_interview(interview_id, current_user)
    if result is None:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return result


@router.patch(
    "/interviews/{interview_id}/reschedule",
    response_model=RescheduleInterviewResponse,
)
async def reschedule_interview(
    interview_id: uuid.UUID,
    request: RescheduleInterviewRequest,
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> RescheduleInterviewResponse:
    """Reschedule a missed assigned interview and optionally notify the candidate."""
    return await service.reschedule_interview(interview_id, request, current_user)


# ------------------------------------------------------------------
# Evaluations
# ------------------------------------------------------------------


@router.get("/evaluations", response_model=EvaluationListResponse)
async def list_evaluations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=50),
    review_state: str = Query(
        default="pending",
        description="pending | completed | all",
    ),
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> EvaluationListResponse:
    """List evaluation sessions filtered by review state."""
    if review_state not in ("pending", "completed", "all"):
        raise HTTPException(
            status_code=400,
            detail="review_state must be pending, completed, or all.",
        )
    return await service.list_evaluations(
        page=page, page_size=page_size, review_state=review_state
    )


@router.get(
    "/evaluations/{session_id}", response_model=EvaluationDetailResponse
)
async def get_evaluation_detail(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> EvaluationDetailResponse:
    """Full evaluation detail with AI scores and per-question breakdown."""
    result = await service.get_evaluation_detail(session_id)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Evaluation session not found."
        )
    return result


@router.post(
    "/evaluations/{session_id}/decision",
    response_model=SubmitDecisionResponse,
)
async def submit_decision(
    session_id: uuid.UUID,
    request: SubmitDecisionRequest,
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> SubmitDecisionResponse:
    """Submit the admin's final decision for an evaluation."""
    try:
        result = await service.submit_decision(
            session_id, request, current_user
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(
            status_code=404, detail="Evaluation session not found."
        )
    return result


# ------------------------------------------------------------------
# Job Roles
# ------------------------------------------------------------------


@router.get("/job-roles", response_model=list[JobRoleItem])
async def list_job_roles(
    current_user: User = Depends(require_roles(RoleName.ADMIN)),
    service: AdminService = Depends(get_admin_service),
) -> list[JobRoleItem]:
    """List all active job roles (for the assign-interview form)."""
    return await service.list_job_roles()
