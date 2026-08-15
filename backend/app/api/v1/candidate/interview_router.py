"""Candidate-facing interview endpoints.

The JD-based practice interview flow surfaces here as a small REST surface:

    POST   /candidate/interviews/practice/jd-based   → start practice
    POST   /candidate/interviews/practice/role-based → start practice
    POST   /candidate/interviews/assigned/{id}/start → start/resume assigned
    GET    /candidate/interviews/sessions/{id}       → refresh-safe state
    POST   /candidate/interviews/sessions/{id}/answers → text answer + next Q
    POST   /candidate/interviews/sessions/{id}/coding-submissions → coding + next Q
    POST   /candidate/interviews/sessions/{id}/submit  → close session + schedule eval

Every route is gated on ``RoleName.CANDIDATE`` and derives the candidate's
identity from the authenticated user's token — no ``candidate_id`` is ever
accepted from the client (an IDOR foothold we categorically refuse).
Ownership of sessions/questions is enforced inside the lifecycle service.
"""

from __future__ import annotations

import uuid
from typing import cast

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm.chat import ChatLLM
from app.api.dependencies.auth import require_roles
from app.api.dependencies.database import get_db
from app.api.v1.candidate.interview_schemas import (
    AnswerSubmissionRequest,
    AnswerSubmissionResponse,
    CodingSubmissionRequest,
    CurrentQuestion,
    InterviewSummary,
    JobRoleResponse,
    PracticeResultResponse,
    SessionStateResponse,
    StartRolePracticeInterviewRequest,
    StartPracticeInterviewRequest,
    StartPracticeInterviewResponse,
    SubmitInterviewResponse,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.enums import RoleName
from app.models.interview_question import InterviewQuestion
from app.models.user import User
from app.repositories.job_role_repository import JobRoleRepository
from app.services.interviews.evaluator import InterviewEvaluator
from app.services.interviews.lifecycle_service import (
    InterviewLifecycleService,
    SessionState,
    StartedInterview,
)
from app.services.interviews.question_planner import JdQuestionPlanner
from infrastructure.database.session import session_scope

logger = get_logger(__name__)
router = APIRouter()


# ---------------------- factory helpers ----------------------


def _build_lifecycle_service(db: AsyncSession) -> InterviewLifecycleService:
    """Assemble the lifecycle service with its LLM-backed collaborators.

    Kept as a plain function (not a FastAPI dependency) so the background
    task can call it with a *different* session at evaluation time.
    """
    chat = ChatLLM()
    planner = JdQuestionPlanner(chat)
    evaluator = InterviewEvaluator(chat)
    return InterviewLifecycleService(
        db,
        planner=planner,
        evaluator=evaluator,
        model_name=settings.llm.model,
    )


def get_lifecycle_service(
    db: AsyncSession = Depends(get_db),
) -> InterviewLifecycleService:
    return _build_lifecycle_service(db)


def get_job_role_repository(
    db: AsyncSession = Depends(get_db),
) -> JobRoleRepository:
    return JobRoleRepository(db)


# ---------------------- endpoints ----------------------


@router.post(
    "/practice/jd-based",
    response_model=StartPracticeInterviewResponse,
    status_code=201,
)
async def start_jd_practice(
    payload: StartPracticeInterviewRequest,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> StartPracticeInterviewResponse:
    """Start a fresh JD-based practice interview.

    Validates the JD, snapshots the candidate's current resume, generates the
    first question via the LLM, and returns everything the player page needs
    to render immediately without a second call.
    """
    started = await service.create_jd_practice(
        candidate=current_user,
        job_description=payload.job_description,
        duration_minutes=payload.duration_minutes,
    )
    return _started_to_response(started, interview_type="PRACTICE", practice_type="JD_BASED")


@router.get("/job-roles", response_model=list[JobRoleResponse])
async def list_job_roles(
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    repository: JobRoleRepository = Depends(get_job_role_repository),
) -> list[JobRoleResponse]:
    del current_user
    roles = await repository.list_active()
    return [JobRoleResponse.model_validate(role) for role in roles]


@router.post(
    "/practice/role-based",
    response_model=StartPracticeInterviewResponse,
    status_code=201,
)
async def start_role_practice(
    payload: StartRolePracticeInterviewRequest,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> StartPracticeInterviewResponse:
    started = await service.create_role_practice(
        candidate=current_user,
        job_role_id=payload.job_role_id,
        custom_role_name=payload.custom_role_name,
        custom_requirements=payload.custom_requirements,
        custom_skills=payload.custom_skills,
        duration_minutes=payload.duration_minutes,
    )
    return _started_to_response(
        started,
        interview_type="PRACTICE",
        practice_type="ROLE_BASED",
        role_name=started.role_name,
    )


@router.post(
    "/assigned/{interview_id}/start",
    response_model=StartPracticeInterviewResponse,
    status_code=201,
)
async def start_assigned_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> StartPracticeInterviewResponse:
    """Create (or resume) a session for an admin-assigned interview.

    The interview row already exists from assignment. This endpoint is what
    actually opens the player: it enforces the access window, snapshots
    planner state from the frozen JD/resume, and returns a ``session_id``.
    Re-joining mid-interview is idempotent.
    """
    started = await service.start_assigned(
        candidate=current_user,
        interview_id=interview_id,
    )
    return _started_to_response(
        started,
        interview_type="ASSIGNED",
        practice_type=None,
        role_name=started.role_name,
    )


@router.get(
    "/sessions/{session_id}",
    response_model=SessionStateResponse,
)
async def get_session_state(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> SessionStateResponse:
    """Return everything needed to (re-)render the interview player.

    Refresh-safe: whatever question the server considers "current" comes back
    here. If the candidate refreshed after answering the current question
    but before submitting the interview, ``existing_answer`` is populated so
    their typed reply isn't lost.
    """
    state = await service.get_state(
        session_id=session_id,
        candidate_id=current_user.id,
    )
    return _session_state_to_response(state)


@router.get(
    "/sessions/{session_id}/result",
    response_model=PracticeResultResponse,
)
async def get_practice_result(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> PracticeResultResponse:
    result = await service.get_practice_result(
        session_id=session_id,
        candidate_id=current_user.id,
    )
    return PracticeResultResponse.model_validate(result, from_attributes=True)


@router.post(
    "/sessions/{session_id}/answers",
    response_model=AnswerSubmissionResponse,
)
async def submit_answer(
    session_id: uuid.UUID,
    payload: AnswerSubmissionRequest,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> AnswerSubmissionResponse:
    outcome = await service.submit_answer(
        session_id=session_id,
        candidate=current_user,
        question_id=payload.question_id,
        answer_text=payload.answer_text,
        response_time_seconds=payload.response_time_seconds,
    )
    state = await service.get_state(
        session_id=session_id, candidate_id=current_user.id
    )
    return AnswerSubmissionResponse(
        next_question=(
            _to_current_question(outcome.next_question)
            if outcome.next_question is not None
            else None
        ),
        is_last_question=outcome.is_last_question,
        total_questions=state.total_questions,
        answered_count=state.answered_count,
    )


@router.post(
    "/sessions/{session_id}/coding-submissions",
    response_model=AnswerSubmissionResponse,
)
async def submit_coding(
    session_id: uuid.UUID,
    payload: CodingSubmissionRequest,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> AnswerSubmissionResponse:
    outcome = await service.submit_coding(
        session_id=session_id,
        candidate=current_user,
        question_id=payload.question_id,
        code=payload.code,
        language=payload.language,
    )
    state = await service.get_state(
        session_id=session_id, candidate_id=current_user.id
    )
    return AnswerSubmissionResponse(
        next_question=(
            _to_current_question(outcome.next_question)
            if outcome.next_question is not None
            else None
        ),
        is_last_question=outcome.is_last_question,
        total_questions=state.total_questions,
        answered_count=state.answered_count,
    )


@router.post(
    "/sessions/{session_id}/submit",
    response_model=SubmitInterviewResponse,
)
async def submit_interview(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_roles(RoleName.CANDIDATE)),
    service: InterviewLifecycleService = Depends(get_lifecycle_service),
) -> SubmitInterviewResponse:
    """Close the interview and schedule background evaluation.

    Returns immediately (evaluation may take 5-30s). The frontend result page
    polls until ``session.status`` becomes ``COMPLETED``.
    """
    outcome = await service.submit_interview(
        session_id=session_id, candidate=current_user
    )
    if outcome.schedule_evaluation:
        background_tasks.add_task(
            _run_evaluation_in_background, outcome.session_id
        )
    return SubmitInterviewResponse(
        session_id=outcome.session_id,
        interview_id=outcome.interview_id,
        status=outcome.status,
        evaluation_status=outcome.evaluation_status,
    )


# ---------------------- helpers ----------------------


async def _run_evaluation_in_background(session_id: uuid.UUID) -> None:
    """Run the evaluator on a fresh DB session (own transaction scope).

    Kept module-level (not a method) so ``BackgroundTasks`` doesn't hold a
    reference to a per-request AsyncSession that FastAPI has already closed
    by the time the task runs.
    """
    try:
        async with session_scope() as db:
            service = _build_lifecycle_service(db)
            await service.evaluate_session(session_id)
    except Exception:  # noqa: BLE001 - swallow so a bad eval doesn't crash the app
        logger.exception(
            "Background evaluation failed for session %s", session_id
        )


def _started_to_response(
    started: StartedInterview,
    *,
    interview_type: str,
    practice_type: str | None,
    role_name: str | None = None,
) -> StartPracticeInterviewResponse:
    return StartPracticeInterviewResponse(
        interview=InterviewSummary(
            id=started.interview_id,
            interview_type=interview_type,
            practice_type=practice_type,
            role_name=role_name,
            duration_minutes=started.duration_minutes,
            status="IN_PROGRESS",
            started_at=None,
        ),
        session_id=started.session_id,
        total_questions=started.total_questions,
        current_question_number=started.first_question.question_number,
        current_question=_to_current_question(started.first_question),
    )


def _to_current_question(question: InterviewQuestion) -> CurrentQuestion:
    existing_answer_text: str | None = None
    if question.answer is not None and question.answer.is_submitted:
        existing_answer_text = question.answer.answer_text
    return CurrentQuestion(
        id=question.id,
        question_number=question.question_number,
        question_text=question.question_text,
        question_type=question.question_type,
        difficulty=question.difficulty,
        topic=question.topic,
        skill=question.skill,
        existing_answer=existing_answer_text,
    )


def _session_state_to_response(state: SessionState) -> SessionStateResponse:
    interview = state.interview
    return SessionStateResponse(
        interview=InterviewSummary(
            id=interview.id,
            interview_type=interview.interview_type,
            practice_type=interview.practice_type,
            role_name=interview.role_name_snapshot,
            duration_minutes=interview.duration_minutes,
            status=interview.status,
            started_at=state.session.started_at,
        ),
        session_id=state.session.id,
        session_status=state.session.status,
        total_questions=state.total_questions,
        answered_count=state.answered_count,
        current_question_number=state.session.current_question_number,
        current_question=(
            _to_current_question(state.current_question)
            if state.current_question is not None
            else None
        ),
        is_last_question=state.is_last_question,
        can_submit=state.can_submit,
        timed_out=getattr(state, "timed_out", False),
    )


# Silence a "cast is unused" lint if a future edit removes casts.
_ = cast
