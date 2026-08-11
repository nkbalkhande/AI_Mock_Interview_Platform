"""Candidate dashboard service.

Aggregates read-only data from several repositories into the DTOs the
dashboard endpoints return. Read-only means no commit here — the service
just composes queries; the request-scoped ``AsyncSession`` yielded by
``get_db`` handles rollback on error.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.candidate.schemas import (
    AssignedResultListItem,
    AssignedResultListResponse,
    AssignedResultSummary,
    CandidateProfileResponse,
    CandidateProfileSummary,
    CandidateProfileUpdateRequest,
    DashboardResponse,
    DashboardStats,
    InterviewHistoryItem,
    InterviewHistoryResponse,
    PracticeResultListItem,
    PracticeResultListResponse,
    PracticeResultSummary,
    RecentResultsResponse,
    UpcomingInterview,
    UpcomingInterviewDetail,
    UpcomingInterviewsResponse,
)
from app.models.interview import Interview
from app.models.interview_evaluation import InterviewEvaluation
from app.models.interview_session import InterviewSession
from app.models.user import User
from app.models.user_profile import UserProfile
from app.repositories.interview_repository import InterviewRepository
from app.repositories.interview_session_repository import InterviewSessionRepository
from app.services.interviews.access_window import access_state


def _coerce_str_list(value: object) -> list[str]:
    """Best-effort coercion for JSONB list columns.

    ``strengths``/``weaknesses``/``improvement_areas`` are JSONB-typed with a
    default of ``[]``, but they may historically contain non-string entries
    (e.g. objects with a ``point`` field). Flatten to a plain ``list[str]``
    so the wire format stays predictable for the frontend.
    """
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


class CandidateDashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.interviews = InterviewRepository(session)
        self.sessions = InterviewSessionRepository(session)

    async def get_dashboard(self, candidate: User) -> DashboardResponse:
        practice_count = await self.interviews.count_by_type(
            candidate.id, interview_type="PRACTICE"
        )
        upcoming_count = await self.interviews.count_upcoming_assigned(candidate.id)
        completed_count = await self.interviews.count_completed(candidate.id)
        average = await self.sessions.average_practice_final_score(candidate.id)

        profile = candidate.profile
        return DashboardResponse(
            profile=CandidateProfileSummary(
                id=candidate.id,
                full_name=candidate.full_name,
                email=candidate.email,
                current_designation=(
                    profile.current_designation if profile else None
                ),
                current_organization=(
                    profile.current_organization if profile else None
                ),
                years_of_experience=(
                    profile.years_of_experience if profile else None
                ),
                profile_photo_path=(
                    profile.profile_photo_path if profile else None
                ),
            ),
            stats=DashboardStats(
                practice_interviews=practice_count,
                upcoming_interviews=upcoming_count,
                completed_interviews=completed_count,
                average_practice_score=average,
            ),
        )

    async def get_upcoming_interviews(
        self, candidate: User, *, limit: int = 20
    ) -> UpcomingInterviewsResponse:
        rows = await self.interviews.list_upcoming(candidate.id, limit=limit)
        items = [self._to_upcoming(row) for row in rows]
        return UpcomingInterviewsResponse(items=items)

    async def get_profile(self, candidate: User) -> CandidateProfileResponse:
        profile = candidate.profile
        return CandidateProfileResponse(
            id=candidate.id,
            full_name=candidate.full_name,
            email=candidate.email,
            current_designation=(profile.current_designation if profile else None),
            current_organization=(profile.current_organization if profile else None),
            years_of_experience=(profile.years_of_experience if profile else None),
            phone_number=(profile.phone_number if profile else None),
            bio=(profile.bio if profile else None),
            profile_photo_path=(profile.profile_photo_path if profile else None),
        )

    async def update_profile_photo(
        self, candidate: User, photo_path: str
    ) -> CandidateProfileResponse:
        if candidate.profile is None:
            candidate.profile = UserProfile(profile_photo_path=photo_path)
        else:
            candidate.profile.profile_photo_path = photo_path

        await self.session.flush()
        await self.session.commit()
        return await self.get_profile(candidate)

    async def update_profile(
        self,
        candidate: User,
        payload: CandidateProfileUpdateRequest,
    ) -> CandidateProfileResponse:
        if candidate.profile is None:
            candidate.profile = UserProfile(
                current_organization=payload.current_organization.strip(),
                current_designation=payload.current_designation.strip(),
                years_of_experience=payload.years_of_experience,
                phone_number=(payload.phone_number.strip() if payload.phone_number else None),
                bio=payload.bio.strip() if payload.bio else None,
            )
        else:
            candidate.full_name = payload.full_name.strip()
            candidate.profile.current_organization = payload.current_organization.strip()
            candidate.profile.current_designation = payload.current_designation.strip()
            candidate.profile.years_of_experience = payload.years_of_experience
            candidate.profile.phone_number = (
                payload.phone_number.strip() if payload.phone_number else None
            )
            candidate.profile.bio = payload.bio.strip() if payload.bio else None

        await self.session.flush()
        await self.session.commit()

        return await self.get_profile(candidate)

    async def get_upcoming_interview_detail(
        self, candidate: User, interview_id: uuid.UUID
    ) -> UpcomingInterviewDetail | None:
        """Fetch full details for one assigned interview owned by this candidate."""
        interview = await self.interviews.get_owned_by_candidate(
            interview_id, candidate.id
        )
        if interview is None:
            return None
        if interview.interview_type != "ASSIGNED":
            return None
        return UpcomingInterviewDetail(
            id=interview.id,
            role=interview.role_name_snapshot,
            organization=None,
            job_description=interview.job_description_snapshot,
            required_experience_min=interview.required_experience_min,
            required_experience_max=interview.required_experience_max,
            scheduled_at=interview.scheduled_at,
            timezone=interview.timezone,
            duration_minutes=interview.duration_minutes,
            status=interview.status,
            access_state=access_state(interview).value,
            access_start_at=interview.access_start_at,
            access_end_at=interview.access_end_at,
            instructions=interview.instructions,
            assigned_by_name=(
                interview.assigned_by_user.full_name
                if interview.assigned_by_user
                else None
            ),
        )

    async def get_recent_results(
        self, candidate: User, *, limit_per_type: int = 5
    ) -> RecentResultsResponse:
        practice_rows = await self.interviews.list_recent_completed(
            candidate.id, limit=limit_per_type, interview_type="PRACTICE"
        )
        assigned_rows = await self.interviews.list_recent_completed(
            candidate.id, limit=limit_per_type, interview_type="ASSIGNED"
        )

        practice = await self._summarise_practice(practice_rows)
        assigned = await self._summarise_assigned(assigned_rows)
        return RecentResultsResponse(practice=practice, assigned=assigned)

    async def get_practice_results(
        self, candidate: User, *, page: int = 1, page_size: int = 20
    ) -> PracticeResultListResponse:
        """Paginated list of all completed practice results."""
        total = await self.interviews.count_completed_by_type(
            candidate.id, interview_type="PRACTICE"
        )
        rows = await self.interviews.list_completed_paginated(
            candidate.id, interview_type="PRACTICE", page=page, page_size=page_size
        )
        items = await self._build_practice_list_items(rows)
        return PracticeResultListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    async def get_assigned_results(
        self, candidate: User, *, page: int = 1, page_size: int = 20
    ) -> AssignedResultListResponse:
        """Paginated list of all completed assigned results."""
        total = await self.interviews.count_completed_by_type(
            candidate.id, interview_type="ASSIGNED"
        )
        rows = await self.interviews.list_completed_paginated(
            candidate.id, interview_type="ASSIGNED", page=page, page_size=page_size
        )
        items = await self._build_assigned_list_items(rows)
        return AssignedResultListResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    async def get_interview_history(
        self,
        candidate: User,
        *,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        type_filter: str | None = None,
    ) -> InterviewHistoryResponse:
        """Full interview history — every interview the candidate started or was assigned."""
        total = await self.interviews.count_history(
            candidate.id,
            status_filter=status_filter,
            type_filter=type_filter,
        )
        rows = await self.interviews.list_history_paginated(
            candidate.id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            type_filter=type_filter,
        )

        interview_ids = [i.id for i in rows]
        finals = await self.sessions.latest_final_evaluation_for_interviews(
            interview_ids
        )

        latest_sessions: dict[uuid.UUID, InterviewSession] = {}
        for interview in rows:
            if interview.sessions:
                latest_sessions[interview.id] = max(
                    interview.sessions, key=lambda s: s.attempt_number
                )

        counts = await self.sessions.question_counts_by_session(
            [s.id for s in latest_sessions.values()]
        )

        items: list[InterviewHistoryItem] = []
        now = datetime.now(timezone.utc)
        for interview in rows:
            latest_session = latest_sessions.get(interview.id)
            evaluation: InterviewEvaluation | None = finals.get(interview.id)
            can_resume = self._can_resume_interview(
                interview, latest_session, now=now
            )

            total_qs, answered = (
                counts.get(latest_session.id, (0, 0))
                if latest_session
                else (0, 0)
            )

            items.append(
                InterviewHistoryItem(
                    interview_id=interview.id,
                    session_id=latest_session.id if latest_session else None,
                    interview_type=interview.interview_type,
                    practice_type=interview.practice_type,
                    role=interview.role_name_snapshot,
                    display_status=self._derive_display_status(
                        interview.status,
                        latest_session.status if latest_session else None,
                        can_resume=can_resume,
                    ),
                    interview_status=interview.status,
                    session_status=(
                        latest_session.status if latest_session else None
                    ),
                    can_resume=can_resume,
                    started_at=(
                        latest_session.started_at if latest_session else None
                    ),
                    last_activity_at=(
                        latest_session.last_activity_at
                        if latest_session
                        else interview.updated_at
                    ),
                    duration_minutes=interview.duration_minutes,
                    overall_score=(
                        evaluation.overall_score if evaluation else None
                    ),
                    answered_count=answered,
                    total_questions=total_qs,
                )
            )

        return InterviewHistoryResponse(
            items=items, total=total, page=page, page_size=page_size
        )

    @staticmethod
    def _derive_display_status(
        interview_status: str,
        session_status: str | None,
        *,
        can_resume: bool,
    ) -> str:
        if interview_status in ("COMPLETED",):
            return "Completed"
        if interview_status in ("CANCELLED",):
            return "Cancelled"
        if interview_status in ("EXPIRED",):
            return "Expired"
        if interview_status in ("SUBMITTED", "AI_EVALUATED", "ADMIN_REVIEW"):
            return "Evaluating"
        if interview_status == "IN_PROGRESS":
            if session_status == "ABANDONED":
                return "Abandoned"
            if session_status == "PAUSED":
                return "Paused" if can_resume else "Interrupted"
            return "In Progress" if can_resume else "Interrupted"
        if interview_status in ("ASSIGNED", "SCHEDULED", "AVAILABLE"):
            return "Not Started"
        return interview_status.replace("_", " ").title()

    @staticmethod
    def _can_resume_interview(
        interview: Interview,
        session: InterviewSession | None,
        *,
        now: datetime,
    ) -> bool:
        if session is None or session.status not in ("IN_PROGRESS", "PAUSED"):
            return False

        if interview.interview_type == "ASSIGNED":
            if interview.access_start_at is not None and now < interview.access_start_at:
                return False
            if interview.access_end_at is not None and now > interview.access_end_at:
                return False
            return True

        if session.started_at is None:
            return False
        started_at = session.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        deadline = started_at + timedelta(minutes=interview.duration_minutes)
        return now < deadline

    # ---- private helpers ------------------------------------------------

    def _to_upcoming(self, interview: Interview) -> UpcomingInterview:
        return UpcomingInterview(
            id=interview.id,
            role=interview.role_name_snapshot,
            # Organization isn't stamped onto the interview row directly today;
            # left null for MVP (can be lifted from ``assigned_by_user.profile``
            # once assignment flow is wired up).
            organization=None,
            job_description=interview.job_description_snapshot,
            required_experience_min=interview.required_experience_min,
            required_experience_max=interview.required_experience_max,
            scheduled_at=interview.scheduled_at,
            timezone=interview.timezone,
            duration_minutes=interview.duration_minutes,
            status=interview.status,
            access_state=access_state(interview).value,
            access_start_at=interview.access_start_at,
            access_end_at=interview.access_end_at,
        )

    async def _summarise_practice(
        self, interviews: Sequence[Interview]
    ) -> list[PracticeResultSummary]:
        if not interviews:
            return []
        ids = [i.id for i in interviews]
        finals = await self.sessions.latest_final_evaluation_for_interviews(ids)
        latest_sessions = await self.sessions.latest_session_by_interview(ids)

        summaries: list[PracticeResultSummary] = []
        for interview in interviews:
            evaluation: InterviewEvaluation | None = finals.get(interview.id)
            session: InterviewSession | None = latest_sessions.get(interview.id)
            summaries.append(
                PracticeResultSummary(
                    interview_id=interview.id,
                    session_id=session.id if session else None,
                    role=interview.role_name_snapshot,
                    completed_at=(session.ended_at if session else None)
                    or interview.updated_at,
                    overall_score=(
                        evaluation.overall_score if evaluation else None
                    ),
                    technical_score=(
                        evaluation.technical_score if evaluation else None
                    ),
                    communication_score=(
                        evaluation.communication_score if evaluation else None
                    ),
                    strengths=_coerce_str_list(
                        evaluation.strengths if evaluation else []
                    ),
                    weaknesses=_coerce_str_list(
                        evaluation.weaknesses if evaluation else []
                    ),
                )
            )
        return summaries

    async def _summarise_assigned(
        self, interviews: Sequence[Interview]
    ) -> list[AssignedResultSummary]:
        if not interviews:
            return []
        ids = [i.id for i in interviews]
        latest_sessions = await self.sessions.latest_session_by_interview(ids)

        summaries: list[AssignedResultSummary] = []
        for interview in interviews:
            session: InterviewSession | None = latest_sessions.get(interview.id)
            decision = session.final_decision if session else None
            summaries.append(
                AssignedResultSummary(
                    interview_id=interview.id,
                    session_id=session.id if session else None,
                    role=interview.role_name_snapshot,
                    completed_at=(session.ended_at if session else None)
                    or interview.updated_at,
                    ai_overall_score=(
                        decision.ai_overall_score if decision else None
                    ),
                    ai_verdict=decision.ai_verdict if decision else None,
                    admin_decision=(
                        decision.admin_decision if decision else None
                    ),
                    admin_feedback=(
                        decision.admin_feedback if decision else None
                    ),
                    result_published_at=(
                        decision.result_published_at if decision else None
                    ),
                )
            )
        return summaries

    async def _build_practice_list_items(
        self, interviews: Sequence[Interview]
    ) -> list[PracticeResultListItem]:
        if not interviews:
            return []
        ids = [i.id for i in interviews]
        finals = await self.sessions.latest_final_evaluation_for_interviews(ids)
        latest_sessions = await self.sessions.latest_session_by_interview(ids)

        items: list[PracticeResultListItem] = []
        for interview in interviews:
            evaluation: InterviewEvaluation | None = finals.get(interview.id)
            session: InterviewSession | None = latest_sessions.get(interview.id)
            items.append(
                PracticeResultListItem(
                    interview_id=interview.id,
                    session_id=session.id if session else None,
                    practice_type=interview.practice_type,
                    role=interview.role_name_snapshot,
                    duration_minutes=interview.duration_minutes,
                    completed_at=(session.ended_at if session else None)
                    or interview.updated_at,
                    overall_score=(
                        evaluation.overall_score if evaluation else None
                    ),
                    technical_score=(
                        evaluation.technical_score if evaluation else None
                    ),
                    communication_score=(
                        evaluation.communication_score if evaluation else None
                    ),
                    reasoning_score=(
                        evaluation.reasoning_score if evaluation else None
                    ),
                    project_knowledge_score=None,
                    ai_verdict=(
                        evaluation.ai_verdict if evaluation else None
                    ),
                    strengths=_coerce_str_list(
                        evaluation.strengths if evaluation else []
                    ),
                    weaknesses=_coerce_str_list(
                        evaluation.weaknesses if evaluation else []
                    ),
                )
            )
        return items

    async def _build_assigned_list_items(
        self, interviews: Sequence[Interview]
    ) -> list[AssignedResultListItem]:
        if not interviews:
            return []
        ids = [i.id for i in interviews]
        latest_sessions = await self.sessions.latest_session_by_interview(ids)

        items: list[AssignedResultListItem] = []
        for interview in interviews:
            session: InterviewSession | None = latest_sessions.get(interview.id)
            decision = session.final_decision if session else None
            items.append(
                AssignedResultListItem(
                    interview_id=interview.id,
                    session_id=session.id if session else None,
                    role=interview.role_name_snapshot,
                    duration_minutes=interview.duration_minutes,
                    completed_at=(session.ended_at if session else None)
                    or interview.updated_at,
                    ai_overall_score=(
                        decision.ai_overall_score if decision else None
                    ),
                    ai_verdict=decision.ai_verdict if decision else None,
                    admin_decision=(
                        decision.admin_decision if decision else None
                    ),
                    admin_feedback=(
                        decision.admin_feedback if decision else None
                    ),
                    result_published_at=(
                        decision.result_published_at if decision else None
                    ),
                )
            )
        return items
