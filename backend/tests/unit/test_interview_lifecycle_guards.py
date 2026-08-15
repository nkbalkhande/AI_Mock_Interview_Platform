from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.exceptions import ConflictError
from app.models.coding_submission import CodingSubmission
from app.services.interviews.lifecycle_service import InterviewLifecycleService


class _FakeDb:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0
        self.rollbacks = 0
        self.flush_error: Exception | None = None

    def add(self, value: Any) -> None:
        if getattr(value, "id", None) is None:
            value.id = uuid.uuid4()
        self.added.append(value)

    async def flush(self) -> None:
        if self.flush_error is not None:
            raise self.flush_error
        return None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class _OwnedSessions:
    def __init__(self, session: Any) -> None:
        self.session = session
        self.lock_calls = 0

    async def get_owned_by_candidate(self, *_: Any) -> Any:
        return self.session

    async def get_owned_for_update(self, *_: Any) -> Any:
        self.lock_calls += 1
        return self.session


class _Events:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def record(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


def _question(
    number: int,
    *,
    stage: str = "TECHNICAL",
    answer: Any = None,
    question_type: str = "TECHNICAL",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        question_number=number,
        question_type=question_type,
        question_text=f"Question {number}",
        expected_answer="Expected",
        evaluation_rubric="Rubric",
        question_metadata={"stage": stage},
        topic="topic",
        skill="skill",
        answer=answer,
    )


def _session(
    *,
    elapsed_minutes: int = 1,
    questions: list[Any] | None = None,
    status: str = "IN_PROGRESS",
    practice_type: str = "ROLE_BASED",
) -> SimpleNamespace:
    interview = SimpleNamespace(
        id=uuid.uuid4(),
        candidate_id=uuid.uuid4(),
        interview_type="PRACTICE",
        practice_type=practice_type,
        role_name_snapshot="AI Engineer",
        resume_version_id=uuid.uuid4(),
        duration_minutes=30,
        status="IN_PROGRESS",
        required_experience_min=None,
        required_experience_max=None,
    )
    return SimpleNamespace(
        id=uuid.uuid4(),
        interview_id=interview.id,
        interview=interview,
        status=status,
        started_at=datetime.now(timezone.utc)
        - timedelta(minutes=elapsed_minutes),
        ended_at=None,
        last_activity_at=None,
        current_question_number=len(questions or []),
        interview_state={
            "duration_minutes": 30,
            "total_target_questions": 7,
            "coverage": {},
        },
        questions=questions or [],
        evaluations=[],
        skill_scores=[],
    )


def _service(db: _FakeDb, session: Any) -> InterviewLifecycleService:
    service = InterviewLifecycleService(
        db,  # type: ignore[arg-type]
        planner=SimpleNamespace(),
        evaluator=SimpleNamespace(),
        model_name="test",
    )
    service._sessions = _OwnedSessions(session)  # type: ignore[assignment]
    service._events = _Events()  # type: ignore[assignment]
    return service


@pytest.mark.asyncio
async def test_expired_state_hides_question_and_allows_controlled_submit() -> None:
    question = _question(1)
    session = _session(elapsed_minutes=31, questions=[question])
    service = _service(_FakeDb(), session)

    state = await service.get_state(
        session_id=session.id,
        candidate_id=session.interview.candidate_id,
    )

    assert state.timed_out is True
    assert state.current_question is None
    assert state.can_submit is True


@pytest.mark.asyncio
async def test_expired_session_rejects_answer_under_row_lock() -> None:
    question = _question(1)
    session = _session(elapsed_minutes=31, questions=[question])
    service = _service(_FakeDb(), session)

    with pytest.raises(ConflictError, match="expired"):
        await service.submit_answer(
            session_id=session.id,
            candidate=SimpleNamespace(id=session.interview.candidate_id),
            question_id=question.id,
            answer_text="late answer",
            response_time_seconds=10,
        )

    assert service._sessions.lock_calls == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_premature_submit_is_rejected() -> None:
    session = _session(questions=[_question(1)])
    service = _service(_FakeDb(), session)

    with pytest.raises(ConflictError, match="not ready"):
        await service.submit_interview(
            session_id=session.id,
            candidate=SimpleNamespace(id=session.interview.candidate_id),
        )


@pytest.mark.asyncio
async def test_submit_claim_contract_prevents_duplicate_evaluator_schedule() -> None:
    answer = SimpleNamespace(
        id=uuid.uuid4(), answer_text="closing", is_submitted=True
    )
    session = _session(
        questions=[_question(1, stage="CLOSING", answer=answer)]
    )
    service = _service(_FakeDb(), session)
    candidate = SimpleNamespace(id=session.interview.candidate_id)

    first = await service.submit_interview(
        session_id=session.id, candidate=candidate
    )
    second = await service.submit_interview(
        session_id=session.id, candidate=candidate
    )

    assert first.schedule_evaluation is True
    assert first.status == "EVALUATING"
    assert second.schedule_evaluation is False
    assert second.evaluation_status == "pending"
    assert "evaluation_started_at" in session.interview_state


@pytest.mark.asyncio
async def test_failed_evaluation_submit_is_claimed_for_retry() -> None:
    session = _session(status="SUBMITTED")
    service = _service(_FakeDb(), session)

    outcome = await service.submit_interview(
        session_id=session.id,
        candidate=SimpleNamespace(id=session.interview.candidate_id),
    )

    assert outcome.schedule_evaluation is True
    assert session.status == "EVALUATING"


@pytest.mark.asyncio
async def test_live_evaluation_lease_does_not_duplicate_worker() -> None:
    session = _session(status="EVALUATING")
    session.interview_state["evaluation_started_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    service = _service(_FakeDb(), session)

    outcome = await service.submit_interview(
        session_id=session.id,
        candidate=SimpleNamespace(id=session.interview.candidate_id),
    )

    assert outcome.schedule_evaluation is False
    assert outcome.evaluation_status == "pending"


@pytest.mark.asyncio
async def test_expired_evaluation_lease_is_atomically_reclaimed() -> None:
    session = _session(status="EVALUATING")
    old_lease = (
        datetime.now(timezone.utc) - timedelta(minutes=6)
    ).isoformat()
    session.interview_state["evaluation_started_at"] = old_lease
    service = _service(_FakeDb(), session)

    outcome = await service.submit_interview(
        session_id=session.id,
        candidate=SimpleNamespace(id=session.interview.candidate_id),
    )

    assert outcome.schedule_evaluation is True
    assert outcome.evaluation_status == "pending"
    assert session.interview_state["evaluation_started_at"] != old_lease


@pytest.mark.asyncio
async def test_answer_retry_preserves_original_and_reuses_existing_next_question() -> None:
    original = SimpleNamespace(
        id=uuid.uuid4(),
        answer_text="original",
        is_submitted=True,
    )
    answered = _question(1, answer=original)
    next_question = _question(2)
    session = _session(questions=[answered, next_question])
    db = _FakeDb()
    service = _service(db, session)

    outcome = await service.submit_answer(
        session_id=session.id,
        candidate=SimpleNamespace(id=session.interview.candidate_id),
        question_id=answered.id,
        answer_text="changed retry",
        response_time_seconds=999,
    )

    assert outcome.saved_answer.answer_text == "original"
    assert outcome.next_question is next_question
    assert service._events.calls == []  # type: ignore[attr-defined]
    assert service._sessions.lock_calls == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_coding_retry_is_idempotent_and_role_source_is_dynamic() -> None:
    original = SimpleNamespace(
        id=uuid.uuid4(),
        answer_text="print('original')",
        is_submitted=True,
    )
    answered = _question(
        1, answer=original, stage="CODING", question_type="CODING"
    )
    next_question = _question(2)
    session = _session(questions=[answered, next_question])
    db = _FakeDb()
    service = _service(db, session)

    retry = await service.submit_coding(
        session_id=session.id,
        candidate=SimpleNamespace(id=session.interview.candidate_id),
        question_id=answered.id,
        code="print('changed')",
        language="python",
    )
    assert retry.saved_answer.answer_text == "print('original')"
    assert not any(isinstance(item, CodingSubmission) for item in db.added)

    fresh_question = _question(
        1, answer=None, stage="CODING", question_type="CODING"
    )
    fresh_session = _session(questions=[fresh_question])
    fresh_service = _service(db, fresh_session)
    fresh_service._answers = SimpleNamespace(  # type: ignore[assignment]
        get_by_question=_async_value(None)
    )
    fresh_service._coding = SimpleNamespace(  # type: ignore[assignment]
        get_final=_async_value(None)
    )
    fresh_service._advance_after_answer = _async_value(None)  # type: ignore[method-assign]

    await fresh_service.submit_coding(
        session_id=fresh_session.id,
        candidate=SimpleNamespace(id=fresh_session.interview.candidate_id),
        question_id=fresh_question.id,
        code="print('fresh')",
        language="python",
    )

    submission = next(
        item for item in db.added if isinstance(item, CodingSubmission)
    )
    assert submission.meta["source"] == "practice_role_based"


@pytest.mark.asyncio
async def test_evaluator_failure_restores_retryable_submitted_state() -> None:
    session = _session(
        questions=[_question(1, answer=SimpleNamespace(answer_text="answer"))],
        status="EVALUATING",
    )
    session.interview_state["target_context"] = {
        "kind": "ROLE",
        "label": "AI Engineer",
        "content": "Role target",
    }
    session.interview_state["evaluation_started_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    db = _FakeDb()
    service = _service(db, session)
    service._load_session_with_interview = _async_value(session)  # type: ignore[method-assign]
    service._evaluator = SimpleNamespace(
        evaluate_role=_async_error(RuntimeError("provider unavailable"))
    )

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await service.evaluate_session(session.id)

    assert db.rollbacks == 1
    assert session.status == "SUBMITTED"
    assert session.interview.status == "SUBMITTED"
    assert "evaluation_started_at" not in session.interview_state
    assert db.commits >= 1


@pytest.mark.asyncio
async def test_persistence_failure_restores_retryable_submitted_state() -> None:
    answer = SimpleNamespace(answer_text="answer", is_submitted=True)
    session = _session(
        questions=[_question(1, answer=answer)],
        status="EVALUATING",
    )
    session.interview_state.update(
        {
            "target_context": {
                "kind": "ROLE",
                "label": "AI Engineer",
                "content": "Role target",
            },
            "evaluation_started_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    db = _FakeDb()
    db.flush_error = RuntimeError("database unavailable")
    service = _service(db, session)
    service._load_session_with_interview = _async_value(session)  # type: ignore[method-assign]
    service._evaluations = SimpleNamespace(  # type: ignore[assignment]
        get_final=_async_value(None)
    )
    service._evaluator = SimpleNamespace(
        evaluate_role=_async_value(_evaluation_result())
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        await service.evaluate_session(session.id)

    assert db.rollbacks == 1
    assert session.status == "SUBMITTED"
    assert session.interview.status == "SUBMITTED"
    assert "evaluation_started_at" not in session.interview_state


@pytest.mark.asyncio
async def test_practice_result_distinguishes_pending_and_retryable() -> None:
    submitted = _session(status="SUBMITTED")
    submitted_service = _service(_FakeDb(), submitted)
    submitted_result = await submitted_service.get_practice_result(
        session_id=submitted.id,
        candidate_id=submitted.interview.candidate_id,
    )

    live = _session(status="EVALUATING")
    live.interview_state["evaluation_started_at"] = datetime.now(
        timezone.utc
    ).isoformat()
    live_result = await _service(_FakeDb(), live).get_practice_result(
        session_id=live.id,
        candidate_id=live.interview.candidate_id,
    )

    expired = _session(status="EVALUATING")
    expired.interview_state["evaluation_started_at"] = (
        datetime.now(timezone.utc) - timedelta(minutes=6)
    ).isoformat()
    expired_result = await _service(_FakeDb(), expired).get_practice_result(
        session_id=expired.id,
        candidate_id=expired.interview.candidate_id,
    )

    assert submitted_result.status == "retryable"
    assert live_result.status == "pending"
    assert expired_result.status == "retryable"


def _async_value(value: Any):
    async def _call(*_: Any, **__: Any) -> Any:
        return value

    return _call


def _async_error(error: Exception):
    async def _call(*_: Any, **__: Any) -> Any:
        raise error

    return _call


def _evaluation_result() -> SimpleNamespace:
    return SimpleNamespace(
        overall_score=7,
        technical_score=7,
        communication_score=7,
        reasoning_score=7,
        project_knowledge_score=7,
        ai_verdict="BORDERLINE",
        confidence=0.7,
        summary="Summary",
        strengths=[],
        weaknesses=[],
        improvement_areas=[],
        skill_scores=[],
        prompt_version="final_evaluator_v2",
    )
