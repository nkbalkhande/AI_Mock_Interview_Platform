"""Unit tests for the v2 JD-based question planner.

The planner is deliberately thin: prompt render → LLM JSON → parse. These
tests exercise the parser (stage validation, difficulty coercion, empty
question rejection, stage→question_type mapping) using a fake LLM.
"""

from __future__ import annotations

from typing import Any

import pytest

from app.ai.llm.chat import LLMError
from app.ai.prompts import (
    JD_QUESTION_PLANNER_VERSION,
    ROLE_QUESTION_PLANNER_VERSION,
)
from app.services.interviews.question_planner import (
    AnswerSnapshot,
    JdQuestionPlanner,
    TargetContext,
)


class _FakeLLM:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.messages: list[Any] = []

    async def complete_json(
        self, messages: list[Any], **_: Any
    ) -> dict[str, Any]:
        self.messages = messages
        return self._response


def _plan_kwargs(**overrides: Any) -> dict[str, Any]:
    """Default kwargs for ``plan_next`` — override per-test as needed."""
    base: dict[str, Any] = {
        "question_number": 1,
        "total_target_questions": 7,
        "interview_duration_minutes": 30,
        "elapsed_time_minutes": 0.0,
        "remaining_time_minutes": 30.0,
        "target_context": TargetContext(
            kind="JD",
            label="Job description",
            content="Senior backend engineer, distributed systems.",
        ),
        "resume_text": "Built high-throughput APIs.",
        "candidate_designation": "Backend Engineer",
        "candidate_experience": "4 years",
        "coverage": None,
        "history": [],
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_planner_returns_technical_question() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Describe how you would design a URL shortener.",
            "topic": "system design",
            "skill": "high-level architecture",
            "difficulty": "hard",
            "stage": "TECHNICAL",
            "expected_answer": "Talk about hash strategy, DB, caching.",
            "evaluation_rubric": "Great: covers scale + tradeoffs.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(**_plan_kwargs(question_number=2))

    assert result.question_text.startswith("Describe how you would design")
    assert result.stage == "TECHNICAL"
    assert result.question_type == "TECHNICAL"
    # Case coerced to upper.
    assert result.difficulty == "HARD"
    assert result.topic == "system design"
    assert result.prompt_version == JD_QUESTION_PLANNER_VERSION


@pytest.mark.asyncio
async def test_planner_introduction_maps_to_behavioral() -> None:
    """INTRODUCTION is a valid stage but must land in a DB-legal type."""
    llm = _FakeLLM(
        {
            "question_text": "To start, tell me about your background.",
            "topic": "introduction",
            "skill": "communication",
            "difficulty": "EASY",
            "stage": "INTRODUCTION",
            "expected_answer": "Summary of relevant experience.",
            "evaluation_rubric": "Strong: clear, relevant, concise.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(**_plan_kwargs(question_number=2))

    assert result.stage == "INTRODUCTION"
    assert result.question_type == "BEHAVIORAL"


@pytest.mark.asyncio
async def test_planner_closing_maps_to_behavioral() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Any questions you'd like to ask us?",
            "topic": "closing",
            "skill": "engagement",
            "difficulty": "EASY",
            "stage": "CLOSING",
            "expected_answer": "Thoughtful, role-specific questions.",
            "evaluation_rubric": "Strong candidates prepare questions in advance.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(
        **_plan_kwargs(
            question_number=7,
            elapsed_time_minutes=27.0,
            remaining_time_minutes=3.0,
        )
    )

    assert result.stage == "CLOSING"
    assert result.question_type == "BEHAVIORAL"


@pytest.mark.asyncio
async def test_planner_coerces_unknown_stage_to_technical() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Explain caching strategies.",
            "topic": "caching",
            "skill": "systems",
            "difficulty": "MEDIUM",
            "stage": "FREESTYLE",  # not a real stage
            "expected_answer": "TTL, invalidation, layers.",
            "evaluation_rubric": "Strong: mentions cache-aside vs write-through.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(**_plan_kwargs(question_number=2))

    assert result.stage == "TECHNICAL"
    assert result.question_type == "TECHNICAL"


@pytest.mark.asyncio
async def test_planner_rejects_empty_question_text() -> None:
    llm = _FakeLLM({"question_text": "   ", "stage": "TECHNICAL"})
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    with pytest.raises(LLMError):
        await planner.plan_next(**_plan_kwargs())


@pytest.mark.asyncio
async def test_planner_coerces_unknown_difficulty_to_medium() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Explain memoization.",
            "topic": "python",
            "skill": "algorithms",
            "difficulty": "brutal",  # unexpected
            "stage": "TECHNICAL",
            "expected_answer": "Cache results of expensive calls.",
            "evaluation_rubric": "Mentions closure or dict cache.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(
        **_plan_kwargs(
            question_number=2,
            history=[
                AnswerSnapshot(
                    question_number=1,
                    question_type="BEHAVIORAL",
                    question_text="Tell me about yourself.",
                    answer_text="I'm a backend engineer.",
                    stage="INTRODUCTION",
                )
            ],
        )
    )

    assert result.difficulty == "MEDIUM"


@pytest.mark.asyncio
async def test_planner_dispatches_role_prompt_without_jd_leakage() -> None:
    llm = _FakeLLM(
        {
            "question_text": "How would you monitor model drift in production?",
            "topic": "model monitoring",
            "skill": "MLOps",
            "difficulty": "MEDIUM",
            "stage": "TECHNICAL",
            "expected_answer": "Discuss drift metrics and alerting.",
            "evaluation_rubric": "Strong answers connect metrics to remediation.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(
        **_plan_kwargs(
            question_number=2,
            target_context=TargetContext(
                kind="ROLE",
                label="AI Engineer",
                content=(
                    "Requirements:\n- Build production AI systems\n"
                    "Skills:\n- Python\n- MLOps\nExperience: 2-6 years"
                ),
            ),
            history=[
                AnswerSnapshot(
                    question_number=1,
                    question_type="BEHAVIORAL",
                    question_text="Tell me about your background.",
                    answer_text="I deployed forecasting models on AWS.",
                    stage="INTRODUCTION",
                )
            ],
        )
    )

    rendered = "\n".join(message.content for message in llm.messages)
    assert "Role being assessed: AI Engineer" in rendered
    assert "Build production AI systems" in rendered
    assert "I deployed forecasting models on AWS." in rendered
    assert "structured role requirements" in rendered.lower()
    assert "broader role competency assessment" in rendered.lower()
    assert "job description" not in rendered.lower()
    assert "vacancy" not in rendered.lower()
    assert result.prompt_version == ROLE_QUESTION_PLANNER_VERSION
    assert result.prompt_version != JD_QUESTION_PLANNER_VERSION


@pytest.mark.asyncio
async def test_planner_dispatches_jd_prompt_without_role_profile_leakage() -> None:
    llm = _FakeLLM(
        {
            "question_text": "How does your API work match this vacancy?",
            "topic": "api design",
            "skill": "backend engineering",
            "difficulty": "MEDIUM",
            "stage": "TECHNICAL",
            "expected_answer": "Relevant examples and trade-offs.",
            "evaluation_rubric": "Strong answers connect evidence to the JD.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(**_plan_kwargs(question_number=2))

    rendered = "\n".join(message.content for message in llm.messages)
    assert "specific vacancy" in rendered.lower()
    assert "required and preferred skills" in rendered.lower()
    assert "resume-to-jd alignment" in rendered.lower()
    assert "broader role competency assessment" not in rendered.lower()
    assert "structured role requirements" not in rendered.lower()
    assert result.prompt_version == JD_QUESTION_PLANNER_VERSION


@pytest.mark.asyncio
async def test_planner_rejects_unsupported_target_kind() -> None:
    llm = _FakeLLM({})
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported target context kind"):
        await planner.plan_next(
            **_plan_kwargs(
                target_context=TargetContext(
                    kind="GENERIC",
                    label="Anything",
                    content="Anything",
                )
            )
        )

    assert llm.messages == []


@pytest.mark.asyncio
async def test_planner_forces_question_one_to_introduction() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Implement an LRU cache.",
            "topic": "algorithms",
            "skill": "coding",
            "difficulty": "HARD",
            "stage": "CODING",
            "expected_answer": "Hash map plus linked list.",
            "evaluation_rubric": "Correct O(1) operations.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(**_plan_kwargs(question_number=1))

    assert result.stage == "INTRODUCTION"
    assert result.question_type == "BEHAVIORAL"
    assert "background" in result.question_text.lower()
