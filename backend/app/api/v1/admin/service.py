"""Admin dashboard service.

Aggregates data from several repositories into the DTOs the admin endpoints
return.  Unlike the candidate service, admin queries are not scoped to a
single user — they see all candidates, interviews, and evaluations.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin.schemas import (
    AdminDashboardResponse,
    AdminDashboardStats,
    AssignInterviewRequest,
    AssignInterviewResponse,
    EvaluationDetailResponse,
    EvaluationListItem,
    EvaluationListResponse,
    InterviewDetailResponse,
    InterviewListItem,
    InterviewListResponse,
    JobRoleItem,
    QuestionEvaluationDetail,
    RecentActivityItem,
    SubmitDecisionRequest,
    SubmitDecisionResponse,
    UpdateUserStatusRequest,
    UpdateUserStatusResponse,
    UserDetailResponse,
    UserInterviewSummary,
    UserListItem,
    UserListResponse,
)
from app.models.final_decision import FinalDecision
from app.models.interview import Interview
from app.models.interview_evaluation import InterviewEvaluation
from app.models.interview_event import InterviewEvent
from app.models.interview_session import InterviewSession
from app.models.notification import Notification
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.models.user import User
from app.repositories.interview_event_repository import InterviewEventRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.interview_session_repository import InterviewSessionRepository
from app.repositories.job_role_repository import JobRoleRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.user_repository import UserRepository


def _coerce_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str):
            out.append(item)
        elif isinstance(item, dict):
            text = item.get("point") or item.get("text") or item.get("value")
            if isinstance(text, str):
                out.append(text)
    return out


def _role_names(user: User) -> list[str]:
    return [ur.role.name for ur in user.user_roles if ur.role is not None]


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.interviews = InterviewRepository(session)
        self.sessions = InterviewSessionRepository(session)
        self.events = InterviewEventRepository(session)
        self.job_roles = JobRoleRepository(session)
        self.notifications = NotificationRepository(session)

    # ------------------------------------------------------------------
    # Dashboard
    # ------------------------------------------------------------------

    async def get_dashboard(self) -> AdminDashboardResponse:
        total_candidates = await self.users.count_candidates()
        total_interviews = await self.interviews.admin_count_all()
        pending_evaluations = await self.sessions.admin_count_pending_review()
        completed_interviews = await self.interviews.admin_count_completed()

        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        stmt = (
            select(InterviewEvent)
            .options(selectinload(InterviewEvent.actor))
            .order_by(InterviewEvent.created_at.desc())
            .limit(10)
        )
        result = await self.session.execute(stmt)
        events: Sequence[InterviewEvent] = result.scalars().all()

        activity = [
            RecentActivityItem(
                id=ev.id,
                event_type=ev.event_type,
                description=_format_event(ev),
                actor_name=ev.actor.full_name if ev.actor else None,
                created_at=ev.created_at,
            )
            for ev in events
        ]

        return AdminDashboardResponse(
            stats=AdminDashboardStats(
                total_candidates=total_candidates,
                total_interviews=total_interviews,
                pending_evaluations=pending_evaluations,
                completed_interviews=completed_interviews,
            ),
            recent_activity=activity,
        )

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    async def list_users(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> UserListResponse:
        total = await self.users.count_filtered(
            search=search, role=role, is_active=is_active
        )
        rows = await self.users.list_paginated(
            page=page,
            page_size=page_size,
            search=search,
            role=role,
            is_active=is_active,
        )
        items = [self._to_user_list_item(u) for u in rows]
        return UserListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    async def get_user_detail(self, user_id: uuid.UUID) -> UserDetailResponse | None:
        user = await self.users.get_detail(user_id)
        if user is None:
            return None

        total_interviews = await self.interviews.admin_count_for_user(user_id)
        interview_rows = await self.interviews.admin_list_for_user(user_id, limit=20)

        profile = user.profile
        return UserDetailResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            email_verified=user.email_verified,
            roles=_role_names(user),
            current_organization=profile.current_organization if profile else None,
            current_designation=profile.current_designation if profile else None,
            years_of_experience=profile.years_of_experience if profile else None,
            phone_number=profile.phone_number if profile else None,
            bio=profile.bio if profile else None,
            profile_photo_path=profile.profile_photo_path if profile else None,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
            total_interviews=total_interviews,
            interviews=[
                UserInterviewSummary(
                    interview_id=iv.id,
                    interview_type=iv.interview_type,
                    role=iv.role_name_snapshot,
                    status=iv.status,
                    scheduled_at=iv.scheduled_at,
                    created_at=iv.created_at,
                )
                for iv in interview_rows
            ],
        )

    async def update_user_status(
        self, user_id: uuid.UUID, request: UpdateUserStatusRequest
    ) -> UpdateUserStatusResponse | None:
        user = await self.users.get_by_id(user_id)
        if user is None:
            return None
        user.is_active = request.is_active
        await self.session.flush()
        await self.session.commit()
        return UpdateUserStatusResponse(id=user.id, is_active=user.is_active)

    # ------------------------------------------------------------------
    # Interviews
    # ------------------------------------------------------------------

    async def list_interviews(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        interview_type: str | None = None,
        search: str | None = None,
    ) -> InterviewListResponse:
        total = await self.interviews.admin_count_filtered(
            status=status, interview_type=interview_type, search=search
        )
        rows = await self.interviews.admin_list_paginated(
            page=page,
            page_size=page_size,
            status=status,
            interview_type=interview_type,
            search=search,
        )
        items = [self._to_interview_list_item(iv) for iv in rows]
        return InterviewListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    async def get_interview_detail(
        self, interview_id: uuid.UUID
    ) -> InterviewDetailResponse | None:
        iv = await self.interviews.admin_get_detail(interview_id)
        if iv is None:
            return None
        return InterviewDetailResponse(
            id=iv.id,
            candidate_id=iv.candidate_id,
            candidate_name=iv.candidate.full_name if iv.candidate else "",
            candidate_email=iv.candidate.email if iv.candidate else "",
            interview_type=iv.interview_type,
            practice_type=iv.practice_type,
            role=iv.role_name_snapshot,
            job_description=iv.job_description_snapshot,
            role_requirements=iv.role_requirements_snapshot,
            required_experience_min=iv.required_experience_min,
            required_experience_max=iv.required_experience_max,
            status=iv.status,
            scheduled_at=iv.scheduled_at,
            timezone=iv.timezone,
            duration_minutes=iv.duration_minutes,
            access_start_at=iv.access_start_at,
            access_end_at=iv.access_end_at,
            instructions=iv.instructions,
            assigned_by_name=(
                iv.assigned_by_user.full_name if iv.assigned_by_user else None
            ),
            created_at=iv.created_at,
            updated_at=iv.updated_at,
        )

    async def assign_interview(
        self, request: AssignInterviewRequest, admin: User
    ) -> AssignInterviewResponse:
        candidate = await self.users.get_by_id(request.candidate_id)
        if candidate is None or not candidate.is_active:
            raise ValueError("Candidate not found or inactive.")

        # Snapshot the candidate's current resume version (if any)
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        resume_stmt = (
            select(Resume)
            .where(Resume.user_id == candidate.id)
            .options(selectinload(Resume.versions))
        )
        resume = (await self.session.execute(resume_stmt)).scalar_one_or_none()

        resume_version_id = None
        if resume:
            current_version = next(
                (v for v in resume.versions if v.is_current), None
            )
            if current_version:
                resume_version_id = current_version.id

        # Look up job role if provided
        job_role = None
        if request.job_role_id:
            job_role = await self.job_roles.get_by_id(request.job_role_id)

        now = datetime.now(timezone.utc)
        access_start = request.scheduled_at - timedelta(minutes=5)
        access_end = request.scheduled_at + timedelta(
            minutes=request.duration_minutes + 10
        )

        interview = Interview(
            candidate_id=candidate.id,
            assigned_by=admin.id,
            job_role_id=request.job_role_id,
            resume_version_id=resume_version_id,
            interview_type="ASSIGNED",
            practice_type=None,
            role_name_snapshot=request.role_name,
            job_description_snapshot=request.job_description,
            role_requirements_snapshot=request.role_requirements or (
                job_role.description if job_role else None
            ),
            required_experience_min=request.required_experience_min,
            required_experience_max=request.required_experience_max,
            scheduled_at=request.scheduled_at,
            timezone=request.timezone,
            duration_minutes=request.duration_minutes,
            access_start_at=access_start,
            access_end_at=access_end,
            status="ASSIGNED",
            instructions=request.instructions,
        )
        self.session.add(interview)
        await self.session.flush()

        await self.events.record(
            interview_id=interview.id,
            session_id=None,
            event_type="INTERVIEW_ASSIGNED",
            actor_user_id=admin.id,
            metadata={
                "candidate_id": str(candidate.id),
                "role": request.role_name,
            },
        )

        notification = Notification(
            user_id=candidate.id,
            type="INTERVIEW_ASSIGNED",
            title="New Interview Assigned",
            message=(
                f"You have been assigned an interview for {request.role_name}. "
                f"Scheduled at {request.scheduled_at.isoformat()}."
            ),
            reference_type="interview",
            reference_id=interview.id,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.commit()

        return AssignInterviewResponse(
            id=interview.id,
            status=interview.status,
            candidate_name=candidate.full_name,
            role=interview.role_name_snapshot,
            scheduled_at=interview.scheduled_at,
        )

    async def cancel_interview(
        self, interview_id: uuid.UUID, admin: User
    ) -> InterviewDetailResponse | None:
        iv = await self.interviews.admin_get_detail(interview_id)
        if iv is None:
            return None

        iv.status = "CANCELLED"
        await self.session.flush()

        await self.events.record(
            interview_id=iv.id,
            session_id=None,
            event_type="INTERVIEW_CANCELLED",
            actor_user_id=admin.id,
        )

        notification = Notification(
            user_id=iv.candidate_id,
            type="INTERVIEW_CANCELLED",
            title="Interview Cancelled",
            message=(
                f"Your interview for {iv.role_name_snapshot or 'N/A'} "
                f"has been cancelled."
            ),
            reference_type="interview",
            reference_id=iv.id,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.commit()

        return await self.get_interview_detail(interview_id)

    # ------------------------------------------------------------------
    # Evaluations
    # ------------------------------------------------------------------

    async def list_evaluations(
        self, *, page: int = 1, page_size: int = 20
    ) -> EvaluationListResponse:
        total = await self.sessions.admin_count_pending_review()
        rows = await self.sessions.admin_list_for_review(
            page=page, page_size=page_size
        )
        items = [self._to_evaluation_list_item(s) for s in rows]
        return EvaluationListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    async def get_evaluation_detail(
        self, session_id: uuid.UUID
    ) -> EvaluationDetailResponse | None:
        session = await self.sessions.admin_get_evaluation_detail(session_id)
        if session is None:
            return None

        interview = session.interview
        candidate = interview.candidate if interview else None
        decision = session.final_decision

        final_eval: InterviewEvaluation | None = next(
            (e for e in session.evaluations if e.evaluation_type == "FINAL"), None
        )

        questions_detail: list[QuestionEvaluationDetail] = []
        for q in sorted(session.questions, key=lambda x: x.question_number):
            q_eval = next(
                (
                    e
                    for e in (q.evaluations if hasattr(q, "evaluations") else [])
                    if e.evaluation_type == "QUESTION"
                ),
                None,
            )
            questions_detail.append(
                QuestionEvaluationDetail(
                    question_number=q.question_number,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    difficulty=q.difficulty,
                    candidate_answer=(
                        q.answer.answer_text if q.answer else None
                    ),
                    expected_answer=q.expected_answer,
                    correctness_score=q_eval.correctness_score if q_eval else None,
                    technical_score=q_eval.technical_score if q_eval else None,
                    communication_score=q_eval.communication_score if q_eval else None,
                    reasoning_score=q_eval.reasoning_score if q_eval else None,
                    overall_score=q_eval.overall_score if q_eval else None,
                    feedback=q_eval.feedback if q_eval else None,
                    strengths=_coerce_str_list(
                        q_eval.strengths if q_eval else []
                    ),
                    weaknesses=_coerce_str_list(
                        q_eval.weaknesses if q_eval else []
                    ),
                )
            )

        return EvaluationDetailResponse(
            session_id=session.id,
            interview_id=interview.id,
            candidate_name=candidate.full_name if candidate else "",
            candidate_email=candidate.email if candidate else "",
            role=interview.role_name_snapshot,
            interview_type=interview.interview_type,
            practice_type=interview.practice_type,
            duration_minutes=interview.duration_minutes,
            scheduled_at=interview.scheduled_at,
            ai_overall_score=final_eval.overall_score if final_eval else None,
            ai_verdict=final_eval.ai_verdict if final_eval else None,
            ai_confidence=final_eval.confidence if final_eval else None,
            ai_summary=final_eval.feedback if final_eval else None,
            ai_strengths=_coerce_str_list(
                final_eval.strengths if final_eval else []
            ),
            ai_weaknesses=_coerce_str_list(
                final_eval.weaknesses if final_eval else []
            ),
            ai_improvement_areas=_coerce_str_list(
                final_eval.improvement_areas if final_eval else []
            ),
            admin_decision=decision.admin_decision if decision else None,
            admin_feedback=decision.admin_feedback if decision else None,
            decided_by_name=(
                decision.decided_by_user.full_name
                if decision and decision.decided_by_user
                else None
            ),
            decided_at=decision.decided_at if decision else None,
            questions=questions_detail,
            session_status=session.status,
            session_started_at=session.started_at,
            session_ended_at=session.ended_at,
        )

    async def submit_decision(
        self,
        session_id: uuid.UUID,
        request: SubmitDecisionRequest,
        admin: User,
    ) -> SubmitDecisionResponse | None:
        session = await self.sessions.admin_get_evaluation_detail(session_id)
        if session is None:
            return None

        allowed = {"CLEARED", "NOT_CLEARED", "NEEDS_FURTHER_REVIEW"}
        if request.admin_decision not in allowed:
            raise ValueError(
                f"admin_decision must be one of {allowed}"
            )

        now = datetime.now(timezone.utc)

        if session.final_decision is None:
            decision = FinalDecision(
                session_id=session.id,
                admin_decision=request.admin_decision,
                admin_feedback=request.admin_feedback,
                decided_by=admin.id,
                decided_at=now,
                result_published_at=now,
            )
            # Copy AI data from FINAL evaluation if available
            final_eval = next(
                (e for e in session.evaluations if e.evaluation_type == "FINAL"),
                None,
            )
            if final_eval:
                decision.ai_verdict = final_eval.ai_verdict
                decision.ai_overall_score = final_eval.overall_score
                decision.ai_summary = final_eval.feedback
                decision.ai_strengths = final_eval.strengths or []
                decision.ai_weaknesses = final_eval.weaknesses or []
                decision.ai_improvement_areas = final_eval.improvement_areas or []
            self.session.add(decision)
        else:
            session.final_decision.admin_decision = request.admin_decision
            session.final_decision.admin_feedback = request.admin_feedback
            session.final_decision.decided_by = admin.id
            session.final_decision.decided_at = now
            session.final_decision.result_published_at = now

        interview = session.interview
        interview.status = "COMPLETED"
        await self.session.flush()

        await self.events.record(
            interview_id=interview.id,
            session_id=session.id,
            event_type="ADMIN_DECISION_MADE",
            actor_user_id=admin.id,
            metadata={
                "decision": request.admin_decision,
            },
        )

        notification = Notification(
            user_id=interview.candidate_id,
            type="RESULT_PUBLISHED",
            title="Interview Result Available",
            message=(
                f"The result for your {interview.role_name_snapshot or ''} "
                f"interview is now available."
            ),
            reference_type="interview",
            reference_id=interview.id,
        )
        self.session.add(notification)
        await self.session.flush()
        await self.session.commit()

        return SubmitDecisionResponse(
            session_id=session.id,
            admin_decision=request.admin_decision,
            decided_at=now,
        )

    # ------------------------------------------------------------------
    # Job Roles
    # ------------------------------------------------------------------

    async def list_job_roles(self) -> list[JobRoleItem]:
        roles = await self.job_roles.list_active()
        return [
            JobRoleItem(
                id=r.id,
                name=r.name,
                description=r.description,
                requirements=r.requirements,
                skills=r.skills,
                experience_min=r.experience_min,
                experience_max=r.experience_max,
                is_active=r.is_active,
            )
            for r in roles
        ]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_user_list_item(user: User) -> UserListItem:
        profile = user.profile
        return UserListItem(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            email_verified=user.email_verified,
            roles=_role_names(user),
            current_organization=profile.current_organization if profile else None,
            current_designation=profile.current_designation if profile else None,
            years_of_experience=profile.years_of_experience if profile else None,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )

    @staticmethod
    def _to_interview_list_item(iv: Interview) -> InterviewListItem:
        return InterviewListItem(
            id=iv.id,
            candidate_id=iv.candidate_id,
            candidate_name=iv.candidate.full_name if iv.candidate else "",
            candidate_email=iv.candidate.email if iv.candidate else "",
            interview_type=iv.interview_type,
            practice_type=iv.practice_type,
            role=iv.role_name_snapshot,
            status=iv.status,
            scheduled_at=iv.scheduled_at,
            duration_minutes=iv.duration_minutes,
            assigned_by_name=(
                iv.assigned_by_user.full_name if iv.assigned_by_user else None
            ),
            created_at=iv.created_at,
        )

    @staticmethod
    def _to_evaluation_list_item(session: InterviewSession) -> EvaluationListItem:
        interview = session.interview
        candidate = interview.candidate if interview else None
        decision = session.final_decision
        final_eval = next(
            (e for e in session.evaluations if e.evaluation_type == "FINAL"), None
        )
        return EvaluationListItem(
            session_id=session.id,
            interview_id=interview.id if interview else uuid.UUID(int=0),
            candidate_name=candidate.full_name if candidate else "",
            candidate_email=candidate.email if candidate else "",
            role=interview.role_name_snapshot if interview else None,
            interview_type=interview.interview_type if interview else "",
            ai_overall_score=final_eval.overall_score if final_eval else None,
            ai_verdict=final_eval.ai_verdict if final_eval else None,
            status=session.status,
            submitted_at=session.ended_at,
        )


def _format_event(event: InterviewEvent) -> str:
    """Human-readable description for a recent-activity row."""
    labels = {
        "INTERVIEW_CREATED": "Interview created",
        "INTERVIEW_ASSIGNED": "Interview assigned",
        "INTERVIEW_SCHEDULED": "Interview scheduled",
        "INTERVIEW_RESCHEDULED": "Interview rescheduled",
        "INTERVIEW_CANCELLED": "Interview cancelled",
        "INTERVIEW_STARTED": "Interview started",
        "INTERVIEW_SUBMITTED": "Interview submitted",
        "AI_EVALUATION_STARTED": "AI evaluation started",
        "AI_EVALUATION_COMPLETED": "AI evaluation completed",
        "ADMIN_REVIEW_STARTED": "Admin review started",
        "ADMIN_DECISION_MADE": "Admin decision submitted",
        "RESULT_PUBLISHED": "Result published",
        "INTERVIEW_EXPIRED": "Interview expired",
    }
    return labels.get(event.event_type, event.event_type.replace("_", " ").title())
