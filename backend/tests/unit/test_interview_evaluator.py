"""Unit tests for the LLM output parser in ``InterviewEvaluator``.

We exercise the parsing / clamping / defaulting logic directly. The LLM
itself is stubbed via a fake ``ChatLLM`` so the tests don't need an API key.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from app.ai.prompts import JD_EVALUATOR_VERSION, ROLE_EVALUATOR_VERSION
from app.services.interviews.evaluator import (
    InterviewEvaluator,
    TranscriptEntry,
)


class _FakeLLM:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.messages_seen: list[Any] = []

    async def complete_json(self, messages: list[Any], **_: Any) -> dict[str, Any]:
        self.messages_seen = messages
        return self._response


@pytest.mark.asyncio
async def test_evaluator_clamps_out_of_range_scores() -> None:
    llm = _FakeLLM(
        {
            "overall_score": 999,
            "technical_score": -5,
            "communication_score": 7.5,
            "problem_solving_score": None,
            "project_knowledge_score": 999,
            "ai_verdict": "cleared",
            "confidence": 2.0,
            "summary": "Solid but rushed at times.",
            "strengths": ["Clear reasoning", ""],
            "weaknesses": ["Skipped edge cases"],
            "improvement_areas": ["Slow down on system design"],
            "skill_scores": [
                {"skill_name": "SQL", "score": 7, "evidence": ["mentioned btree"]},
                {"skill_name": "", "score": 5},  # dropped: empty name
                {"score": 5},  # dropped: no name
                {"skill_name": "Python", "score": "not-a-number"},  # dropped
            ],
        }
    )
    evaluator = InterviewEvaluator(llm)  # type: ignore[arg-type]

    result = await evaluator.evaluate_jd(
        job_description="Backend engineer.",
        resume_text="Wrote APIs.",
        candidate_designation="Backend Engineer",
        candidate_experience="3 years",
        transcript=[
            TranscriptEntry(
                question_number=1,
                question_type="TECHNICAL",
                question_text="What is a btree?",
                expected_answer="A balanced tree used by DB indexes.",
                evaluation_rubric="Should mention balance + log(n) lookups.",
                answer_text="Btrees are self-balancing.",
            )
        ],
    )

    assert result.overall_score == Decimal("10")
    assert result.technical_score == Decimal("0")
    assert result.communication_score == Decimal("7.5")
    assert result.reasoning_score == Decimal("0")  # None coerced
    assert result.project_knowledge_score == Decimal("10")
    assert result.ai_verdict == "CLEARED"
    assert result.confidence == Decimal("1")
    # Empty strings dropped from strengths
    assert result.strengths == ["Clear reasoning"]
    assert result.weaknesses == ["Skipped edge cases"]
    # Only SQL survives — the others are filtered
    assert len(result.skill_scores) == 1
    assert result.skill_scores[0].skill_name == "SQL"
    assert result.skill_scores[0].evidence == ["mentioned btree"]
    assert result.prompt_version == JD_EVALUATOR_VERSION
    assert "JOB DESCRIPTION ALIGNMENT" in llm.messages_seen[0].content
    assert '"project_knowledge_score": number' in llm.messages_seen[0].content


@pytest.mark.asyncio
async def test_evaluator_coerces_unexpected_verdict_to_borderline() -> None:
    llm = _FakeLLM(
        {
            "overall_score": 5,
            "technical_score": 5,
            "communication_score": 5,
            "problem_solving_score": 5,
            "ai_verdict": "unknown_verdict",
            "confidence": 0.4,
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "improvement_areas": [],
            "skill_scores": [],
        }
    )
    evaluator = InterviewEvaluator(llm)  # type: ignore[arg-type]

    result = await evaluator.evaluate_jd(
        job_description="JD",
        resume_text=None,
        candidate_designation=None,
        candidate_experience=None,
        transcript=[],
    )

    assert result.ai_verdict == "BORDERLINE"
    assert result.project_knowledge_score == Decimal("0")


@pytest.mark.asyncio
async def test_evaluator_deduplicates_normalized_truncated_skill_names() -> None:
    long_name = "Architecture " + ("X" * 200)
    llm = _FakeLLM(
        {
            "overall_score": 7,
            "technical_score": 7,
            "communication_score": 7,
            "problem_solving_score": 7,
            "project_knowledge_score": 7,
            "ai_verdict": "BORDERLINE",
            "confidence": 0.7,
            "summary": "Solid.",
            "strengths": [],
            "weaknesses": [],
            "improvement_areas": [],
            "skill_scores": [
                {"skill_name": " Python ", "score": 8},
                {"skill_name": "python", "score": 2},
                {"skill_name": long_name, "score": 6},
                {"skill_name": long_name.lower(), "score": 9},
                {"skill_name": ["invalid"], "score": 5},
                {"skill_name": "SQL", "score": {"bad": True}},
            ],
        }
    )
    evaluator = InterviewEvaluator(llm)  # type: ignore[arg-type]

    result = await evaluator.evaluate_role(
        target_label="Backend Engineer",
        role_profile="Core competencies: Python, SQL, system design",
        resume_text=None,
        candidate_designation=None,
        candidate_experience=None,
        transcript=[],
    )

    assert [score.skill_name for score in result.skill_scores] == [
        "Python",
        long_name[:150],
    ]
    assert result.prompt_version == ROLE_EVALUATOR_VERSION
    assert "ROLE COMPETENCY ALIGNMENT" in llm.messages_seen[0].content
