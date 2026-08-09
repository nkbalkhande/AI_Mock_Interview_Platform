"""End-to-end lifecycle for JD-based practice interviews.

This service is the single choreographer of the practice flow:

    create_jd_practice → get_state (many times) →
        submit_answer / submit_coding (many times) →
        submit_interview → evaluate_session (background)

Every state transition emits an ``interview_events`` row so the audit trail
matches the product requirement. Ownership is enforced by every mutation
path: repository methods only return sessions/interviews when the
``candidate_id`` matches; a missing return raises ``NotFoundError``.

Duration-driven flow (v2):

- The service does NOT hardcode a fixed question type distribution. It
  derives a target question count from ``duration_minutes`` (see
  ``_compute_target_questions``) and passes pacing signals (elapsed /
  remaining minutes) plus a lightweight coverage state to the LLM planner
  on every turn.
- The planner picks the next STAGE
  (INTRODUCTION|TECHNICAL|PROJECT|CODING|BEHAVIORAL|CLOSING) itself. The
  stage is stored on the question in ``question_metadata.stage`` while the
  DB column ``question_type`` receives a mapped value from ``_STAGE_TO_TYPE``
  so we stay inside the existing CHECK constraint.
- Termination: the interview ends when the target count is reached OR the
  most-recently-answered question was in stage CLOSING. A hard cap prevents
  runaway loops if the planner ever refuses to close.

Concurrency / idempotency:

- If a candidate re-submits an already-answered question (refresh, double
  click), we upsert the answer instead of erroring, and re-return whichever
  next question was previously generated. No wasted LLM calls, no duplicate
  rows.
- Submitting an interview twice is a no-op after the first transition —
  status guards protect from re-entry.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import set_committed_value

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from app.core.logging import get_logger
from app.models.coding_submission import CodingSubmission
from app.models.interview import Interview
from app.models.interview_answer import InterviewAnswer
from app.models.interview_evaluation import InterviewEvaluation
from app.models.interview_question import InterviewQuestion
from app.models.interview_session import InterviewSession
from app.models.job_role import JobRole
from app.models.skill_score import SkillScore
from app.models.user import User
from app.repositories.coding_submission_repository import (
    CodingSubmissionRepository,
)
from app.repositories.interview_answer_repository import (
    InterviewAnswerRepository,
)
from app.repositories.interview_evaluation_repository import (
    InterviewEvaluationRepository,
)
from app.repositories.interview_event_repository import (
    InterviewEventRepository,
)
from app.repositories.interview_question_repository import (
    InterviewQuestionRepository,
)
from app.repositories.interview_repository import InterviewRepository
from app.repositories.interview_session_repository import (
    InterviewSessionRepository,
)
from app.repositories.job_role_repository import JobRoleRepository
from app.services.interviews.evaluator import (
    InterviewEvaluator,
    TranscriptEntry,
)
from app.services.interviews.question_planner import (
    AnswerSnapshot,
    JdQuestionPlanner,
    TargetContext,
)
from app.services.resumes.current_resume_loader import (
    CurrentResume,
    CurrentResumeLoader,
)

logger = get_logger(__name__)


# JD validation constraints — chosen to filter out obvious garbage (a single
# word, or a whole book) without being annoying for real job descriptions.
JD_MIN_CHARS = 200
JD_MAX_CHARS = 20000

# Cap on resume text captured into the session snapshot. Longer than the
# planner prompt limit so the evaluator (which sees more context per turn)
# has room; still bounded to keep JSONB size in check.
_RESUME_SNAPSHOT_CHAR_LIMIT = 12000

# Duration bounds for the JD-based practice interview. Matches the
# ``interviews.duration_minutes > 0 AND <= 180`` DB CHECK, tightened to a
# sensible product range.
DURATION_MIN_MINUTES = 15
DURATION_MAX_MINUTES = 90
DEFAULT_DURATION_MINUTES = 30

ROLE_REQUIREMENTS_MAX_ITEMS = 20
ROLE_REQUIREMENT_MAX_CHARS = 300
ROLE_SKILLS_MAX_ITEMS = 30
ROLE_SKILL_MAX_CHARS = 100

# A crashed background worker must not strand a result forever. The claim is
# stored in interview_state because it is session-specific and does not
# require interpreting unrelated activity timestamps.
_EVALUATION_LEASE = timedelta(minutes=5)

# Absolute hard cap on questions per session — the planner should always
# resolve before this, but if the model insists on continuing we stop.
_HARD_QUESTION_CAP = 20

# Terminal states — anything past IN_PROGRESS is not answerable/re-startable.
_TERMINAL_STATUSES = {"SUBMITTED", "EVALUATING", "EVALUATED", "COMPLETED", "ABANDONED"}


# Empty coverage state stamped onto a new session. Keeps the shape stable so
# the planner's coverage-summary formatter never has to defend against missing
# keys.
def _initial_coverage() -> dict:
    return {
        "introduction_completed": False,
        "project_discussed": False,
        "coding_completed": False,
        "behavioral_completed": False,
        "closing_completed": False,
        "technical_topics": [],
        "technical_count": 0,
    }


def _compute_target_questions(duration_minutes: int) -> int:
    """Duration → target question count.

    Rough calibration from the product spec:
      15 min → 5   (Intro → Tech → Project → Tech → Closing)
      30 min → 7   (Intro → 2×Tech → Project → Coding → Behavioral → Closing)
      45 min → 8
      60 min → 9
    Beyond 60 min we add ~1 question per 15 min, capped at the hard limit.
    """
    d = max(1, int(duration_minutes))
    if d <= 15:
        return 5
    if d <= 30:
        return 7
    if d <= 45:
        return 8
    if d <= 60:
        return 9
    extra = (d - 60) // 15
    return min(_HARD_QUESTION_CAP - 2, 9 + extra)


@dataclass(frozen=True)
class StartedInterview:
    interview_id: uuid.UUID
    session_id: uuid.UUID
    total_questions: int
    duration_minutes: int
    first_question: InterviewQuestion
    role_name: str | None = None


@dataclass(frozen=True)
class SessionState:
    """Snapshot returned by ``get_state`` — everything the UI needs.

    ``current_question`` is ``None`` once every planned question has been
    asked *and* answered — that's the "ready to submit" state the frontend
    turns into a "Submit Interview" CTA.
    """

    session: InterviewSession
    interview: Interview
    total_questions: int
    answered_count: int
    current_question: InterviewQuestion | None
    is_last_question: bool
    can_submit: bool
    timed_out: bool


@dataclass(frozen=True)
class AnswerOutcome:
    """Return value of ``submit_answer`` / ``submit_coding``.

    ``next_question`` is ``None`` when the last planned question has just
    been answered — the caller should then show the "Submit Interview" CTA.
    """

    saved_answer: InterviewAnswer
    next_question: InterviewQuestion | None
    is_last_question: bool


@dataclass(frozen=True)
class SubmitOutcome:
    session_id: uuid.UUID
    interview_id: uuid.UUID
    status: str
    evaluation_status: str
    schedule_evaluation: bool


@dataclass(frozen=True)
class PracticeResult:
    session_id: uuid.UUID
    status: str
    practice_type: str
    role_name: str | None
    overall_score: float | None = None
    technical_score: float | None = None
    communication_score: float | None = None
    reasoning_score: float | None = None
    project_knowledge_score: float | None = None
    ai_verdict: str | None = None
    confidence: float | None = None
    summary: str | None = None
    strengths: list[str] | None = None
    weaknesses: list[str] | None = None
    improvement_areas: list[str] | None = None
    skill_scores: list[dict] | None = None


class InterviewLifecycleService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        planner: JdQuestionPlanner,
        evaluator: InterviewEvaluator,
        model_name: str,
    ) -> None:
        self._session = session
        self._interviews = InterviewRepository(session)
        self._sessions = InterviewSessionRepository(session)
        self._questions = InterviewQuestionRepository(session)
        self._answers = InterviewAnswerRepository(session)
        self._coding = CodingSubmissionRepository(session)
        self._events = InterviewEventRepository(session)
        self._evaluations = InterviewEvaluationRepository(session)
        self._job_roles = JobRoleRepository(session)
        self._resume_loader = CurrentResumeLoader(session)
        self._planner = planner
        self._evaluator = evaluator
        self._model_name = model_name

    # ---------------------- creation ----------------------

    async def create_jd_practice(
        self,
        *,
        candidate: User,
        job_description: str,
        duration_minutes: int | None = None,
    ) -> StartedInterview:
        """Create the interview + session + first question in one transaction.

        The candidate's current resume is snapshotted onto the interview and
        into the session's ``interview_state`` so future resume edits don't
        rewrite history. The first question is generated via the LLM before
        we return so the frontend can render it immediately.

        ``duration_minutes`` drives the target question count and the pacing
        signals passed to the planner on every turn. It's clamped to
        ``[DURATION_MIN_MINUTES, DURATION_MAX_MINUTES]``.
        """
        jd = (job_description or "").strip()
        if len(jd) < JD_MIN_CHARS:
            raise ValidationError(
                f"Job description must be at least {JD_MIN_CHARS} characters."
            )
        if len(jd) > JD_MAX_CHARS:
            raise ValidationError(
                f"Job description must be at most {JD_MAX_CHARS} characters."
            )

        duration = _resolve_duration(duration_minutes)
        total_target = _compute_target_questions(duration)

        resume = await self._resume_loader.get_current_for_user(candidate.id)
        if resume is None:
            raise BusinessRuleError(
                "Please upload a resume before starting a JD-based practice interview."
            )

        designation, experience = _extract_profile_summary(candidate)

        interview = Interview(
            candidate_id=candidate.id,
            interview_type="PRACTICE",
            practice_type="JD_BASED",
            job_description_snapshot=jd,
            resume_version_id=resume.version_id,
            duration_minutes=duration,
            status="IN_PROGRESS",
        )
        self._session.add(interview)
        await self._session.flush()

        started_at = datetime.now(timezone.utc)
        session = InterviewSession(
            interview_id=interview.id,
            attempt_number=1,
            status="IN_PROGRESS",
            started_at=started_at,
            last_activity_at=started_at,
            current_question_number=0,
            interview_state={
                "duration_minutes": duration,
                "total_target_questions": total_target,
                "coverage": _initial_coverage(),
                "resume_snippet": _snapshot_resume_text(resume),
                "resume_version_id": str(resume.version_id),
                "resume_file_name": resume.file_name,
                "candidate_designation": designation,
                "candidate_experience": experience,
                "target_context": {
                    "kind": "JD",
                    "label": "Job description",
                    "content": jd,
                },
                "prompt_version_planner": None,  # set below when planner runs
            },
        )
        self._session.add(session)
        await self._session.flush()

        await self._events.record(
            interview_id=interview.id,
            session_id=None,
            event_type="INTERVIEW_CREATED",
            actor_user_id=candidate.id,
            metadata={
                "interview_type": "PRACTICE",
                "practice_type": "JD_BASED",
                "duration_minutes": duration,
                "total_target_questions": total_target,
            },
        )
        await self._events.record(
            interview_id=interview.id,
            session_id=session.id,
            event_type="INTERVIEW_STARTED",
            actor_user_id=candidate.id,
            metadata={"attempt_number": session.attempt_number},
        )

        # ``session.questions`` has never been loaded (this session was just
        # added), so we must NOT let the planner call read it — that would
        # trigger a lazy load and blow up under asyncpg. First question →
        # empty history.
        first_question = await self._generate_and_persist_question(
            interview=interview,
            session=session,
            resume=resume,
            candidate=candidate,
            question_number=1,
            history=[],
        )

        # Commit here so a subsequent GET can immediately see the row. All
        # services in this codebase own their own transaction (mirrors
        # ``AuthService.register_candidate``).
        await self._session.commit()

        return StartedInterview(
            interview_id=interview.id,
            session_id=session.id,
            total_questions=total_target,
            duration_minutes=interview.duration_minutes,
            first_question=first_question,
        )

    async def create_role_practice(
        self,
        *,
        candidate: User,
        job_role_id: uuid.UUID | None,
        custom_role_name: str | None,
        custom_requirements: list[str] | None,
        custom_skills: list[str] | None,
        duration_minutes: int | None = None,
    ) -> StartedInterview:
        """Create a role-based practice run from a catalog or custom snapshot."""
        if (job_role_id is None) == (custom_role_name is None):
            raise ValidationError(
                "Choose exactly one catalog role or provide one custom role."
            )

        role: JobRole | None = None
        if job_role_id is not None:
            role = await self._job_roles.get_active(job_role_id)
            if role is None:
                raise NotFoundError("Job role not found.")
            role_name = role.name
            requirements = _clean_string_list(
                role.requirements,
                max_items=ROLE_REQUIREMENTS_MAX_ITEMS,
                max_item_chars=ROLE_REQUIREMENT_MAX_CHARS,
            )
            skills = _clean_string_list(
                role.skills,
                max_items=ROLE_SKILLS_MAX_ITEMS,
                max_item_chars=ROLE_SKILL_MAX_CHARS,
            )
            experience_min = role.experience_min
            experience_max = role.experience_max
        else:
            role_name = (custom_role_name or "").strip()
            requirements = _clean_string_list(
                custom_requirements,
                max_items=ROLE_REQUIREMENTS_MAX_ITEMS,
                max_item_chars=ROLE_REQUIREMENT_MAX_CHARS,
            )
            skills = _clean_string_list(
                custom_skills,
                max_items=ROLE_SKILLS_MAX_ITEMS,
                max_item_chars=ROLE_SKILL_MAX_CHARS,
            )
            if len(role_name) < 2 or not requirements:
                raise ValidationError(
                    "Custom role name and at least one requirement are required."
                )
            experience_min = None
            experience_max = None

        duration = _resolve_duration(duration_minutes)
        total_target = _compute_target_questions(duration)
        resume = await self._resume_loader.get_current_for_user(candidate.id)
        if resume is None:
            raise BusinessRuleError(
                "Please upload a resume before starting a role-based practice interview."
            )

        designation, experience = _extract_profile_summary(candidate)
        role_snapshot = {
            "name": role_name,
            "requirements": requirements,
            "skills": skills,
            "experience_min": (
                float(experience_min) if experience_min is not None else None
            ),
            "experience_max": (
                float(experience_max) if experience_max is not None else None
            ),
        }
        target_content = _format_role_target(role_snapshot)
        interview = Interview(
            candidate_id=candidate.id,
            interview_type="PRACTICE",
            practice_type="ROLE_BASED",
            job_role_id=role.id if role is not None else None,
            role_name_snapshot=role_name,
            role_requirements_snapshot=json.dumps(role_snapshot),
            required_experience_min=experience_min,
            required_experience_max=experience_max,
            resume_version_id=resume.version_id,
            duration_minutes=duration,
            status="IN_PROGRESS",
        )
        self._session.add(interview)
        await self._session.flush()

        started_at = datetime.now(timezone.utc)
        session = InterviewSession(
            interview_id=interview.id,
            attempt_number=1,
            status="IN_PROGRESS",
            started_at=started_at,
            last_activity_at=started_at,
            current_question_number=0,
            interview_state={
                "duration_minutes": duration,
                "total_target_questions": total_target,
                "coverage": _initial_coverage(),
                "resume_snippet": _snapshot_resume_text(resume),
                "resume_version_id": str(resume.version_id),
                "resume_file_name": resume.file_name,
                "candidate_designation": designation,
                "candidate_experience": experience,
                "role_snapshot": role_snapshot,
                "target_context": {
                    "kind": "ROLE",
                    "label": role_name,
                    "content": target_content,
                },
                "prompt_version_planner": None,
            },
        )
        self._session.add(session)
        await self._session.flush()

        await self._events.record(
            interview_id=interview.id,
            session_id=None,
            event_type="INTERVIEW_CREATED",
            actor_user_id=candidate.id,
            metadata={
                "interview_type": "PRACTICE",
                "practice_type": "ROLE_BASED",
                "role_name": role_name,
                "duration_minutes": duration,
                "total_target_questions": total_target,
            },
        )
        await self._events.record(
            interview_id=interview.id,
            session_id=session.id,
            event_type="INTERVIEW_STARTED",
            actor_user_id=candidate.id,
            metadata={"attempt_number": session.attempt_number},
        )
        first_question = await self._generate_and_persist_question(
            interview=interview,
            session=session,
            resume=resume,
            candidate=candidate,
            question_number=1,
            history=[],
        )
        await self._session.commit()
        return StartedInterview(
            interview_id=interview.id,
            session_id=session.id,
            total_questions=total_target,
            duration_minutes=duration,
            first_question=first_question,
            role_name=role_name,
        )

    # ---------------------- read ----------------------

    async def get_state(
        self,
        *,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> SessionState:
        session = await self._sessions.get_owned_by_candidate(
            session_id, candidate_id
        )
        if session is None:
            raise NotFoundError("Interview session not found.")

        interview = session.interview
        state = session.interview_state or {}
        total = _read_total_target(state)

        questions = sorted(session.questions, key=lambda q: q.question_number)
        answered = sum(
            1 for q in questions if q.answer is not None and q.answer.is_submitted
        )

        # "Current" = highest-numbered question. If it's already answered
        # AND we haven't hit the target, the mid-loop crash recovery is
        # handled by ``_advance_after_answer`` on the next submit; here we
        # just show the last generated question.
        current: InterviewQuestion | None = questions[-1] if questions else None

        last_stage = _question_stage(current) if current is not None else None
        # Interview ends when we've hit the target OR the last question was
        # a CLOSING one and its answer is in.
        target_reached = answered >= total
        closing_answered = (
            last_stage == "CLOSING"
            and current is not None
            and current.answer is not None
            and current.answer.is_submitted
        )
        timed_out = session.status == "IN_PROGRESS" and _is_timed_out(session)
        can_submit = session.status == "IN_PROGRESS" and (
            target_reached or closing_answered or timed_out
        )
        is_last = current is not None and (
            current.question_number >= total or last_stage == "CLOSING"
        )

        if timed_out:
            current = None
            is_last = True

        # Once submitted/evaluated/completed, don't leak the last question as
        # "the one to answer now" — the UI should show a "session finished"
        # state and redirect to the result page.
        if session.status in _TERMINAL_STATUSES:
            current = None
            can_submit = False

        return SessionState(
            session=session,
            interview=interview,
            total_questions=total,
            answered_count=answered,
            current_question=current,
            is_last_question=is_last,
            can_submit=can_submit,
            timed_out=timed_out,
        )

    async def get_practice_result(
        self,
        *,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> PracticeResult:
        """Return an ownership-scoped persisted practice evaluation."""
        session = await self._sessions.get_owned_by_candidate(
            session_id, candidate_id
        )
        if (
            session is None
            or session.interview.interview_type != "PRACTICE"
        ):
            raise NotFoundError("Interview session not found.")

        final = next(
            (
                evaluation
                for evaluation in session.evaluations
                if evaluation.evaluation_type == "FINAL"
            ),
            None,
        )
        if final is None:
            result_status = (
                "retryable"
                if session.status == "SUBMITTED"
                or (
                    session.status == "EVALUATING"
                    and _evaluation_lease_expired(session)
                )
                else "pending"
            )
            return PracticeResult(
                session_id=session.id,
                status=result_status,
                practice_type=session.interview.practice_type or "",
                role_name=session.interview.role_name_snapshot,
                strengths=[],
                weaknesses=[],
                improvement_areas=[],
                skill_scores=[],
            )

        metadata = final.evaluation_metadata or {}
        return PracticeResult(
            session_id=session.id,
            status="completed",
            practice_type=session.interview.practice_type or "",
            role_name=session.interview.role_name_snapshot,
            overall_score=_as_float(final.overall_score),
            technical_score=_as_float(final.technical_score),
            communication_score=_as_float(final.communication_score),
            reasoning_score=_as_float(final.reasoning_score),
            project_knowledge_score=_as_float(
                metadata.get("project_knowledge_score")
            ),
            ai_verdict=final.ai_verdict,
            confidence=_as_float(final.confidence),
            summary=final.feedback,
            strengths=list(final.strengths or []),
            weaknesses=list(final.weaknesses or []),
            improvement_areas=list(final.improvement_areas or []),
            skill_scores=[
                {
                    "skill_name": score.skill_name,
                    "score": float(score.score),
                    "max_score": float(score.max_score),
                    "strength": score.strength,
                    "improvement_area": score.improvement_area,
                    "evidence": list(score.evidence or []),
                }
                for score in session.skill_scores
            ],
        )

    # ---------------------- answer submission ----------------------

    async def submit_answer(
        self,
        *,
        session_id: uuid.UUID,
        candidate: User,
        question_id: uuid.UUID,
        answer_text: str,
        response_time_seconds: int | None,
    ) -> AnswerOutcome:
        session, question = await self._load_answerable_question(
            session_id=session_id,
            candidate_id=candidate.id,
            question_id=question_id,
        )
        if question.question_type == "CODING":
            raise BusinessRuleError(
                "This question is a coding question; use the coding submission endpoint."
            )
        if question.answer is not None and question.answer.is_submitted:
            outcome = _existing_answer_outcome(session, question)
            await self._session.commit()
            return outcome

        answer = await self._upsert_answer(
            question=question,
            answer_text=answer_text,
            response_time_seconds=response_time_seconds,
            answer_metadata={},
        )
        await self._events.record(
            interview_id=session.interview_id,
            session_id=session.id,
            event_type="ANSWER_SUBMITTED",
            actor_user_id=candidate.id,
            metadata={"question_id": str(question.id)},
        )

        next_q = await self._advance_after_answer(
            session=session,
            candidate=candidate,
            answered_question=question,
        )
        await self._session.commit()

        return AnswerOutcome(
            saved_answer=answer,
            next_question=next_q,
            is_last_question=next_q is None,
        )

    async def submit_coding(
        self,
        *,
        session_id: uuid.UUID,
        candidate: User,
        question_id: uuid.UUID,
        code: str,
        language: str,
    ) -> AnswerOutcome:
        session, question = await self._load_answerable_question(
            session_id=session_id,
            candidate_id=candidate.id,
            question_id=question_id,
        )
        if question.question_type != "CODING":
            raise BusinessRuleError(
                "This question is not a coding question."
            )
        if question.answer is not None and question.answer.is_submitted:
            outcome = _existing_answer_outcome(session, question)
            await self._session.commit()
            return outcome

        code = (code or "").strip()
        if not code:
            raise ValidationError("Code submission cannot be empty.")
        language = (language or "").strip().lower()
        if not language:
            raise ValidationError("Programming language is required.")

        # Store the code both as the answer_text (so the transcript picks it
        # up) and as a coding_submissions row (so the shape of the domain
        # data is right for any future runner integration).
        answer = await self._upsert_answer(
            question=question,
            answer_text=code,
            response_time_seconds=None,
            answer_metadata={"language": language, "type": "coding"},
        )

        # A row lock protects this check + insert. If a final submission is
        # already present, treat this request as an idempotent retry.
        existing_final = await self._coding.get_final(question.id)
        if existing_final is not None:
            await self._session.commit()
            return _existing_answer_outcome(session, question)

        submission = CodingSubmission(
            question_id=question.id,
            answer_id=answer.id,
            code=code,
            language=language,
            is_final_submission=True,
            meta={
                "source": (
                    f"practice_{(session.interview.practice_type or 'unknown').lower()}"
                )
            },
        )
        self._session.add(submission)
        await self._session.flush()

        await self._events.record(
            interview_id=session.interview_id,
            session_id=session.id,
            event_type="CODING_SUBMISSION",
            actor_user_id=candidate.id,
            metadata={
                "question_id": str(question.id),
                "language": language,
            },
        )

        next_q = await self._advance_after_answer(
            session=session,
            candidate=candidate,
            answered_question=question,
        )
        await self._session.commit()

        return AnswerOutcome(
            saved_answer=answer,
            next_question=next_q,
            is_last_question=next_q is None,
        )

    # ---------------------- submit interview ----------------------

    async def submit_interview(
        self,
        *,
        session_id: uuid.UUID,
        candidate: User,
    ) -> SubmitOutcome:
        session = await self._sessions.get_owned_for_update(
            session_id, candidate.id
        )
        if session is None:
            raise NotFoundError("Interview session not found.")

        if session.status in {"EVALUATED", "COMPLETED"}:
            return SubmitOutcome(
                session_id=session.id,
                interview_id=session.interview_id,
                status=session.status,
                evaluation_status="ready",
                schedule_evaluation=False,
            )
        if session.status == "EVALUATING" and not _evaluation_lease_expired(
            session
        ):
            return SubmitOutcome(
                session_id=session.id,
                interview_id=session.interview_id,
                status=session.status,
                evaluation_status="pending",
                schedule_evaluation=False,
            )

        retrying_failed_evaluation = session.status in {
            "SUBMITTED",
            "EVALUATING",
        }
        if session.status not in {"IN_PROGRESS", "SUBMITTED", "EVALUATING"}:
            raise ConflictError(
                f"Session is in state {session.status!r}, cannot be submitted."
            )

        if not retrying_failed_evaluation and not _submission_eligible(session):
            raise ConflictError(
                "Interview is not ready to submit. Complete the closing question "
                "or wait until the duration expires."
            )

        now = datetime.now(timezone.utc)
        session.status = "EVALUATING"
        session.ended_at = session.ended_at or now
        session.last_activity_at = now
        session.interview_state = {
            **(session.interview_state or {}),
            "evaluation_started_at": now.isoformat(),
        }
        session.interview.status = "SUBMITTED"

        if not retrying_failed_evaluation:
            await self._events.record(
                interview_id=session.interview_id,
                session_id=session.id,
                event_type="INTERVIEW_SUBMITTED",
                actor_user_id=candidate.id,
                metadata={"timed_out": _is_timed_out(session)},
            )
        await self._session.commit()
        return SubmitOutcome(
            session_id=session.id,
            interview_id=session.interview_id,
            status=session.status,
            evaluation_status="pending",
            schedule_evaluation=True,
        )

    # ---------------------- evaluation (background) ----------------------

    async def evaluate_session(self, session_id: uuid.UUID) -> None:
        """Run the FINAL evaluator and persist the result.

        Intended to be scheduled by FastAPI's ``BackgroundTasks`` right after
        ``submit_interview`` returns. Safe to invoke twice — a duplicate call
        finds the session already ``EVALUATED`` and returns without running
        the LLM again.
        """
        session = await self._load_session_with_interview(session_id)
        if session is None:
            logger.warning("evaluate_session: no such session %s", session_id)
            return

        if session.status in {"EVALUATED", "COMPLETED"}:
            return
        if session.status != "SUBMITTED" and session.status != "EVALUATING":
            logger.warning(
                "evaluate_session: skipping session %s in status %s",
                session_id,
                session.status,
            )
            return

        try:
            now = datetime.now(timezone.utc)
            session.status = "EVALUATING"
            if not (session.interview_state or {}).get(
                "evaluation_started_at"
            ):
                session.interview_state = {
                    **(session.interview_state or {}),
                    "evaluation_started_at": now.isoformat(),
                }
            await self._session.commit()

            # Reload with all related data eager-loaded to build the transcript.
            session_full = await self._sessions.get_owned_by_candidate(
                session_id, session.interview.candidate_id
            )
            assert session_full is not None  # the claimed row still exists
            interview = session_full.interview
            transcript = _build_transcript(session_full)
            evaluation_state = session_full.interview_state or {}
            evaluation_target = _read_target_context(
                interview, evaluation_state
            )

            if evaluation_target.kind == "ROLE":
                result = await self._evaluator.evaluate_role(
                    target_label=evaluation_target.label,
                    role_profile=evaluation_target.content,
                    resume_text=evaluation_state.get("resume_snippet"),
                    candidate_designation=evaluation_state.get(
                        "candidate_designation"
                    ),
                    candidate_experience=evaluation_state.get(
                        "candidate_experience"
                    ),
                    transcript=transcript,
                )
            else:
                result = await self._evaluator.evaluate_jd(
                    job_description=evaluation_target.content,
                    resume_text=evaluation_state.get("resume_snippet"),
                    candidate_designation=evaluation_state.get(
                        "candidate_designation"
                    ),
                    candidate_experience=evaluation_state.get(
                        "candidate_experience"
                    ),
                    transcript=transcript,
                )

            # Guard against duplicate FINAL rows (partial unique index).
            existing_final = await self._evaluations.get_final(session_full.id)
            if existing_final is None:
                evaluation = InterviewEvaluation(
                    session_id=session_full.id,
                    question_id=None,
                    evaluation_type="FINAL",
                    overall_score=result.overall_score,
                    technical_score=result.technical_score,
                    communication_score=result.communication_score,
                    reasoning_score=result.reasoning_score,
                    ai_verdict=result.ai_verdict,
                    confidence=result.confidence,
                    feedback=result.summary,
                    strengths=list(result.strengths),
                    weaknesses=list(result.weaknesses),
                    improvement_areas=list(result.improvement_areas),
                    model_name=self._model_name,
                    prompt_version=result.prompt_version,
                    evaluation_metadata={
                        "project_knowledge_score": float(
                            result.project_knowledge_score
                        )
                    },
                )
                self._session.add(evaluation)
                await self._session.flush()

                # Skill scores — unique on (session_id, skill_name).
                persisted_skill_names: set[str] = set()
                for sk in result.skill_scores:
                    skill_name = sk.skill_name.strip()[:150]
                    normalized_name = skill_name.casefold()
                    if (
                        not skill_name
                        or normalized_name in persisted_skill_names
                    ):
                        continue
                    persisted_skill_names.add(normalized_name)
                    self._session.add(
                        SkillScore(
                            session_id=session_full.id,
                            skill_name=skill_name,
                            score=sk.score,
                            max_score=Decimal("10"),
                            strength=sk.strength,
                            improvement_area=sk.improvement_area,
                            evidence=list(sk.evidence),
                        )
                    )
                await self._session.flush()

            session_full.status = "EVALUATED"
            interview.status = "AI_EVALUATED"

            await self._events.record(
                interview_id=interview.id,
                session_id=session_full.id,
                event_type="AI_EVALUATION_COMPLETED",
                actor_user_id=None,
                metadata={
                    "model_name": self._model_name,
                    "prompt_version": result.prompt_version,
                },
            )

            # Practice interviews have no admin review → mark COMPLETED so the
            # candidate's result page can render immediately.
            session_full.status = "COMPLETED"
            session_full.interview_state = {
                key: value
                for key, value in (session_full.interview_state or {}).items()
                if key != "evaluation_started_at"
            }
            interview.status = "COMPLETED"
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            retry_session = await self._load_session_with_interview(session_id)
            if retry_session is not None:
                retry_session.status = "SUBMITTED"
                retry_session.interview.status = "SUBMITTED"
                retry_session.interview_state = {
                    key: value
                    for key, value in (
                        retry_session.interview_state or {}
                    ).items()
                    if key != "evaluation_started_at"
                }
                await self._session.commit()
            raise

    # ---------------------- internals ----------------------

    async def _load_session_with_interview(
        self, session_id: uuid.UUID
    ) -> InterviewSession | None:
        """Fetch a session with its parent interview eager-loaded.

        Used by the background evaluator: at that point we don't yet know
        the candidate_id, so we can't use the ownership-scoped helper — the
        session came from an already-authorized submit call.
        """
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .options(selectinload(InterviewSession.interview))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _load_answerable_question(
        self,
        *,
        session_id: uuid.UUID,
        candidate_id: uuid.UUID,
        question_id: uuid.UUID,
    ) -> tuple[InterviewSession, InterviewQuestion]:
        session = await self._sessions.get_owned_for_update(
            session_id, candidate_id
        )
        if session is None:
            raise NotFoundError("Interview session not found.")

        if session.status != "IN_PROGRESS":
            raise ConflictError(
                f"Session is in state {session.status!r}, cannot accept answers."
            )
        if _is_timed_out(session):
            raise ConflictError(
                "Interview duration has expired; submit the interview for evaluation."
            )

        question = next(
            (q for q in session.questions if q.id == question_id), None
        )
        if question is None:
            # Either the question doesn't exist or belongs to another session
            # (fetched via URL manipulation) — same 404 in both cases.
            raise NotFoundError("Question not found in this session.")

        return session, question

    async def _upsert_answer(
        self,
        *,
        question: InterviewQuestion,
        answer_text: str,
        response_time_seconds: int | None,
        answer_metadata: dict,
    ) -> InterviewAnswer:
        answer = await self._answers.get_by_question(question.id)
        now = datetime.now(timezone.utc)
        if answer is not None and answer.is_submitted:
            return answer
        if answer is None:
            answer = InterviewAnswer(
                question_id=question.id,
                answer_text=answer_text,
                answered_at=now,
                response_time_seconds=response_time_seconds,
                is_submitted=True,
                answer_metadata=answer_metadata,
            )
            self._session.add(answer)
        else:
            answer.answer_text = answer_text
            answer.answered_at = now
            if response_time_seconds is not None:
                answer.response_time_seconds = response_time_seconds
            answer.is_submitted = True
            merged = {**(answer.answer_metadata or {}), **answer_metadata}
            answer.answer_metadata = merged
        await self._session.flush()
        question.answer = answer
        return answer

    async def _advance_after_answer(
        self,
        *,
        session: InterviewSession,
        candidate: User,
        answered_question: InterviewQuestion,
    ) -> InterviewQuestion | None:
        """Produce the next question if we still have room.

        Termination rules (any triggers "return None"):
          - the just-answered question was in stage ``CLOSING``,
          - we've asked ``total_target_questions`` questions,
          - safety cap ``_HARD_QUESTION_CAP`` reached.

        Otherwise, update coverage from the answered question and delegate
        to the planner for the next one.
        """
        session.last_activity_at = datetime.now(timezone.utc)

        # If a later-numbered question already exists (e.g. a duplicate
        # submit), skip regeneration and just return it.
        for q in session.questions:
            if q.question_number > answered_question.question_number:
                return q

        state = dict(session.interview_state or {})
        total_target = _read_total_target(state)

        # Update coverage using the stage the planner recorded on the answered
        # question (falls back to question_type when older rows are around).
        coverage = _bump_coverage(
            dict(state.get("coverage") or _initial_coverage()),
            question=answered_question,
        )
        state["coverage"] = coverage
        session.interview_state = state

        # Termination checks.
        last_stage = _question_stage(answered_question)
        if last_stage == "CLOSING":
            return None
        if answered_question.question_number >= total_target:
            return None
        if answered_question.question_number >= _HARD_QUESTION_CAP:
            logger.warning(
                "Hard question cap hit for session %s at Q%d",
                session.id,
                answered_question.question_number,
            )
            return None

        # Load the current resume snapshot from interview_state; we snapshotted
        # it on creation so we don't need to re-hit resume_versions.
        resume_snippet = state.get("resume_snippet")
        # Repackage as CurrentResume for the shared helper.
        resume = CurrentResume(
            version_id=session.interview.resume_version_id or uuid.uuid4(),
            extracted_text=resume_snippet,
            file_name=state.get("resume_file_name") or "resume",
        )
        # session.questions is eager-loaded (get_owned_by_candidate uses
        # selectinload), and each question's ``answer`` is loaded too — so
        # it's safe to build history from it here without triggering an
        # async lazy load.
        history: list[AnswerSnapshot] = [
            AnswerSnapshot(
                question_number=q.question_number,
                question_type=q.question_type,
                question_text=q.question_text,
                answer_text=q.answer.answer_text if q.answer else None,
                stage=_question_stage(q),
            )
            for q in sorted(session.questions, key=lambda q: q.question_number)
        ]
        next_number = answered_question.question_number + 1
        return await self._generate_and_persist_question(
            interview=session.interview,
            session=session,
            resume=resume,
            candidate=candidate,
            question_number=next_number,
            history=history,
        )

    async def _generate_and_persist_question(
        self,
        *,
        interview: Interview,
        session: InterviewSession,
        resume: CurrentResume,
        candidate: User,
        question_number: int,
        history: list[AnswerSnapshot],
    ) -> InterviewQuestion:
        """Ask the planner for the next question and persist it.

        ``history`` is passed in by the caller rather than derived from
        ``session.questions`` — this method must never touch an unloaded
        relationship, because it can be invoked on a *freshly added*
        session (create_jd_practice) whose collections have never been
        loaded, and lazy-loading from asyncpg raises MissingGreenlet.
        """
        state = dict(session.interview_state or {})
        duration = int(state.get("duration_minutes") or interview.duration_minutes)
        total_target = _read_total_target(state)
        elapsed, remaining = _elapsed_and_remaining_minutes(
            started_at=session.started_at, duration_minutes=duration
        )
        coverage = dict(state.get("coverage") or _initial_coverage())

        planned = await self._planner.plan_next(
            question_number=question_number,
            total_target_questions=total_target,
            interview_duration_minutes=duration,
            elapsed_time_minutes=elapsed,
            remaining_time_minutes=remaining,
            target_context=_read_target_context(interview, state),
            resume_text=resume.extracted_text,
            candidate_designation=state.get("candidate_designation"),
            candidate_experience=state.get("candidate_experience"),
            coverage=coverage,
            history=history,
        )
        if question_number == 1 and planned.stage != "INTRODUCTION":
            planned = replace(
                planned,
                question_text=(
                    "To start, please introduce yourself and summarize your "
                    "background and relevant experience."
                ),
                question_type="BEHAVIORAL",
                stage="INTRODUCTION",
                difficulty="EASY",
                topic="introduction",
                skill="communication",
            )

        question = InterviewQuestion(
            session_id=session.id,
            question_number=question_number,
            question_text=planned.question_text,
            question_type=planned.question_type,
            difficulty=planned.difficulty,
            topic=planned.topic or None,
            skill=planned.skill or None,
            source="AI_GENERATED",
            expected_answer=planned.expected_answer or None,
            evaluation_rubric=planned.evaluation_rubric or None,
            question_metadata={
                "prompt_version": planned.prompt_version,
                "model_name": self._model_name,
                # True stage as decided by the LLM. Kept here (rather than
                # collapsed into question_type) so the evaluator + coverage
                # tracker can reconstruct the actual interview flow.
                "stage": planned.stage,
            },
        )
        self._session.add(question)
        await self._session.flush()
        # Freshly-inserted question has no answer yet — tell SQLA the
        # relationship is *loaded* with None so the router serializer
        # (``_to_current_question``) doesn't try to lazy-load it and
        # crash under asyncpg.
        set_committed_value(question, "answer", None)

        session.current_question_number = question_number
        state["prompt_version_planner"] = planned.prompt_version
        session.interview_state = state

        await self._events.record(
            interview_id=interview.id,
            session_id=session.id,
            event_type="QUESTION_ASKED",
            actor_user_id=candidate.id,
            metadata={
                "question_number": question_number,
                "question_type": planned.question_type,
                "stage": planned.stage,
                "topic": planned.topic,
                "skill": planned.skill,
            },
        )

        return question


# ---------------------- module helpers ----------------------


def _existing_answer_outcome(
    session: InterviewSession, question: InterviewQuestion
) -> AnswerOutcome:
    answer = question.answer
    assert answer is not None and answer.is_submitted
    next_question = next(
        (
            candidate
            for candidate in sorted(
                session.questions, key=lambda item: item.question_number
            )
            if candidate.question_number > question.question_number
        ),
        None,
    )
    return AnswerOutcome(
        saved_answer=answer,
        next_question=next_question,
        is_last_question=next_question is None,
    )


def _is_timed_out(session: InterviewSession) -> bool:
    if session.started_at is None:
        return False
    started_at = session.started_at
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    duration = int(
        (session.interview_state or {}).get("duration_minutes")
        or session.interview.duration_minutes
    )
    elapsed = datetime.now(timezone.utc) - started_at
    return elapsed.total_seconds() >= duration * 60


def _evaluation_lease_expired(session: InterviewSession) -> bool:
    raw_started_at = (session.interview_state or {}).get(
        "evaluation_started_at"
    )
    if not isinstance(raw_started_at, str):
        return True
    try:
        started_at = datetime.fromisoformat(
            raw_started_at.replace("Z", "+00:00")
        )
    except ValueError:
        return True
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) >= started_at + _EVALUATION_LEASE


def _submission_eligible(session: InterviewSession) -> bool:
    if _is_timed_out(session):
        return True
    questions = sorted(session.questions, key=lambda item: item.question_number)
    answered = [
        question
        for question in questions
        if question.answer is not None and question.answer.is_submitted
    ]
    if len(answered) >= _read_total_target(session.interview_state or {}):
        return True
    if not questions:
        return False
    last = questions[-1]
    return (
        _question_stage(last) == "CLOSING"
        and last.answer is not None
        and last.answer.is_submitted
    )


def _resolve_duration(value: int | None) -> int:
    """Clamp the requested duration to the supported product range."""
    if value is None:
        return DEFAULT_DURATION_MINUTES
    if not isinstance(value, int):  # pragma: no cover - pydantic already ints
        try:
            value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Duration must be an integer number of minutes.") from exc
    if value < DURATION_MIN_MINUTES or value > DURATION_MAX_MINUTES:
        raise ValidationError(
            "Interview duration must be between "
            f"{DURATION_MIN_MINUTES} and {DURATION_MAX_MINUTES} minutes."
        )
    return value


def _read_total_target(state: dict | None) -> int:
    """Recover the target question count from the session state.

    Falls back to computing it from ``duration_minutes`` if the state was
    written by an older code path (defensive; new sessions always have it).
    """
    if not state:
        return _compute_target_questions(DEFAULT_DURATION_MINUTES)
    total = state.get("total_target_questions")
    if isinstance(total, int) and total > 0:
        return total
    duration = state.get("duration_minutes")
    if isinstance(duration, int) and duration > 0:
        return _compute_target_questions(duration)
    return _compute_target_questions(DEFAULT_DURATION_MINUTES)


def _elapsed_and_remaining_minutes(
    *, started_at: datetime | None, duration_minutes: int
) -> tuple[float, float]:
    """Compute (elapsed, remaining) in floating-point minutes.

    ``started_at`` can be missing (e.g. very early state); treat as "just
    started" so the planner still receives usable pacing signals.
    """
    now = datetime.now(timezone.utc)
    start = started_at or now
    # Guard against naive datetimes drifting in from unexpected code paths.
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    elapsed_seconds = max(0.0, (now - start).total_seconds())
    elapsed_min = elapsed_seconds / 60.0
    remaining_min = max(0.0, float(duration_minutes) - elapsed_min)
    return elapsed_min, remaining_min


def _question_stage(question: InterviewQuestion | None) -> str | None:
    """Read the planner-recorded stage from a question's metadata."""
    if question is None:
        return None
    metadata = question.question_metadata or {}
    stage = metadata.get("stage")
    if isinstance(stage, str) and stage:
        return stage.upper()
    # Historical rows without ``stage`` fall back to question_type — good
    # enough to keep termination + coverage sensible on legacy data.
    q_type = question.question_type
    return q_type.upper() if isinstance(q_type, str) and q_type else None


def _bump_coverage(coverage: dict, *, question: InterviewQuestion) -> dict:
    """Update the coverage dict after ``question`` was answered.

    Deterministic bookkeeping only — no LLM required. Skill-level analysis
    (``weak_areas`` etc.) is left to the FINAL evaluator, which has the
    full transcript.
    """
    stage = _question_stage(question) or ""
    if stage == "INTRODUCTION":
        coverage["introduction_completed"] = True
    elif stage == "PROJECT":
        coverage["project_discussed"] = True
    elif stage == "CODING":
        coverage["coding_completed"] = True
    elif stage == "BEHAVIORAL":
        coverage["behavioral_completed"] = True
    elif stage == "CLOSING":
        coverage["closing_completed"] = True
    elif stage == "TECHNICAL":
        coverage["technical_count"] = int(coverage.get("technical_count") or 0) + 1

    topic = (question.topic or "").strip()
    if topic:
        topics = list(coverage.get("technical_topics") or [])
        if topic not in topics:
            topics.append(topic)
        coverage["technical_topics"] = topics[:20]  # cap to keep JSONB small

    return coverage


def _snapshot_resume_text(resume: CurrentResume) -> str | None:
    if not resume.has_text:
        return None
    text = resume.extracted_text or ""
    if len(text) <= _RESUME_SNAPSHOT_CHAR_LIMIT:
        return text
    return text[:_RESUME_SNAPSHOT_CHAR_LIMIT]


def _clean_string_list(
    values: object,
    *,
    max_items: int,
    max_item_chars: int,
) -> list[str]:
    if not isinstance(values, list):
        return []
    cleaned: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        item = value.strip()
        if not item or len(item) > max_item_chars:
            continue
        cleaned.append(item)
        if len(cleaned) >= max_items:
            break
    return cleaned


def _format_role_target(snapshot: dict) -> str:
    requirements = "\n".join(
        f"- {item}" for item in snapshot.get("requirements", [])
    ) or "- (not specified)"
    skills = "\n".join(
        f"- {item}" for item in snapshot.get("skills", [])
    ) or "- (not specified)"
    minimum = snapshot.get("experience_min")
    maximum = snapshot.get("experience_max")
    if minimum is None and maximum is None:
        experience = "(not specified)"
    elif maximum is None:
        experience = f"{minimum}+ years"
    else:
        experience = f"{minimum}-{maximum} years"
    return (
        f"Role: {snapshot.get('name')}\n"
        f"Requirements:\n{requirements}\n"
        f"Skills:\n{skills}\n"
        f"Experience: {experience}"
    )


def _read_target_context(interview: Interview, state: dict) -> TargetContext:
    stored = state.get("target_context")
    if isinstance(stored, dict):
        stored_kind = str(stored.get("kind") or "JD")
        # Backward-compatible read for sessions created before prompt dispatch
        # used the concise JD kind.
        if stored_kind == "JOB_DESCRIPTION":
            stored_kind = "JD"
        return TargetContext(
            kind=stored_kind,
            label=str(stored.get("label") or "Job description"),
            content=str(stored.get("content") or ""),
        )
    return TargetContext(
        kind="JD",
        label="Job description",
        content=interview.job_description_snapshot or "",
    )


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_profile_summary(user: User) -> tuple[str | None, str | None]:
    """Return (designation, experience_display) from the user's profile.

    Kept forgiving: the interview flow should still work if the profile
    hasn't loaded some fields yet.
    """
    profile = getattr(user, "profile", None)
    if profile is None:
        return None, None
    designation = getattr(profile, "current_designation", None)
    experience_years = getattr(profile, "years_of_experience", None)
    experience_display: str | None
    if experience_years is None:
        experience_display = None
    else:
        experience_display = f"{experience_years} years"
    return designation, experience_display


def _build_transcript(
    session: InterviewSession,
) -> list[TranscriptEntry]:
    transcript: list[TranscriptEntry] = []
    for q in sorted(session.questions, key=lambda q: q.question_number):
        answer_text = q.answer.answer_text if q.answer else None
        transcript.append(
            TranscriptEntry(
                question_number=q.question_number,
                question_type=q.question_type,
                question_text=q.question_text,
                expected_answer=q.expected_answer,
                evaluation_rubric=q.evaluation_rubric,
                answer_text=answer_text,
            )
        )
    return transcript
