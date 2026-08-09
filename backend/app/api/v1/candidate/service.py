"""Candidate dashboard service.

Aggregates read-only data from several repositories into the DTOs the
dashboard endpoints return. Read-only means no commit here — the service
just composes queries; the request-scoped ``AsyncSession`` yielded by
``get_db`` handles rollback on error.
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.candidate.schemas import (
    AssignedResultSummary,
    CandidateProfileSummary,
    DashboardResponse,
    DashboardStats,
    PracticeResultSummary,
    RecentResultsResponse,
    UpcomingInterview,
    UpcomingInterviewsResponse,
)
from app.models.interview import Interview
from app.models.interview_evaluation import InterviewEvaluation
from app.models.interview_session import InterviewSession
from app.models.user import User
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
