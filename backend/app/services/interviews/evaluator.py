"""FINAL evaluator for a completed practice session.

Runs the LLM once with the entire transcript + JD/role-profile + resume +
rubrics and returns a validated ``EvaluationResult`` dataclass. The lifecycle
service is responsible for persisting the result into the database — this
module does no IO other than calling the LLM.

Supports two evaluation modes:
- **JD-based:** evaluates candidate alignment with a specific Job Description.
- **Role-based:** evaluates candidate competency for a general role profile.

Design notes:

- Score fields on ``interview_evaluations`` are ``Numeric(5, 2)`` with a
  CHECK constraint of 0..10, so we clamp any values the model returns.
- ``ai_verdict`` is stored on the practice evaluation but is never a hiring
  decision (practice interviews have no admin review). It's kept for
  consistency and future analytics.
- Skill scores follow the same 0..10 scale (see ``skill_scores.max_score``
  default of 10 in the ORM).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.ai.llm.chat import ChatLLM, ChatMessage, LLMError
from app.ai.prompts import (
    JD_EVALUATOR_PROMPT,
    JD_EVALUATOR_VERSION,
    ROLE_EVALUATOR_PROMPT,
    ROLE_EVALUATOR_VERSION,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

_ALLOWED_VERDICTS = {"CLEARED", "NOT_CLEARED", "BORDERLINE"}
_RESUME_CONTEXT_CHAR_LIMIT = 6000
_JD_CONTEXT_CHAR_LIMIT = 6000
_TRANSCRIPT_CHAR_LIMIT = 12000


@dataclass(frozen=True)
class TranscriptEntry:
    question_number: int
    question_type: str
    question_text: str
    expected_answer: str | None
    evaluation_rubric: str | None
    answer_text: str | None


@dataclass(frozen=True)
class SkillScoreResult:
    skill_name: str
    score: Decimal
    strength: str | None
    improvement_area: str | None
    evidence: list[str]


@dataclass(frozen=True)
class EvaluationResult:
    overall_score: Decimal
    technical_score: Decimal
    communication_score: Decimal
    reasoning_score: Decimal
    project_knowledge_score: Decimal
    ai_verdict: str
    confidence: Decimal
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    improvement_areas: list[str]
    skill_scores: list[SkillScoreResult]
    prompt_version: str
    model_name: str


class InterviewEvaluator:
    """LLM-backed final evaluator for practice sessions."""

    def __init__(self, llm: ChatLLM) -> None:
        self._llm = llm

    async def evaluate_jd(
        self,
        *,
        job_description: str,
        resume_text: str | None,
        candidate_designation: str | None,
        candidate_experience: str | None,
        transcript: list[TranscriptEntry],
        required_experience: str | None = None,
    ) -> EvaluationResult:
        """Evaluate a JD-based practice interview."""
        transcript_block = self._format_transcript(transcript)
        system_text, user_text = JD_EVALUATOR_PROMPT.render(
            candidate_designation=candidate_designation or "(unspecified)",
            candidate_experience=candidate_experience or "(unspecified)",
            required_experience=required_experience
            or "(not specified — use the experience stated in the JD, else the candidate's experience)",
            resume_text=_truncate(
                resume_text or "(no resume text available)",
                _RESUME_CONTEXT_CHAR_LIMIT,
            ),
            job_description=_truncate(job_description, _JD_CONTEXT_CHAR_LIMIT),
            transcript=transcript_block,
        )
        raw = await self._llm.complete_json(
            [
                ChatMessage(role="system", content=system_text),
                ChatMessage(role="user", content=user_text),
            ]
        )
        return self._parse(raw, JD_EVALUATOR_VERSION)

    async def evaluate_role(
        self,
        *,
        target_label: str,
        role_profile: str,
        resume_text: str | None,
        candidate_designation: str | None,
        candidate_experience: str | None,
        transcript: list[TranscriptEntry],
        required_experience: str | None = None,
    ) -> EvaluationResult:
        """Evaluate a role-based practice interview."""
        transcript_block = self._format_transcript(transcript)
        system_text, user_text = ROLE_EVALUATOR_PROMPT.render(
            candidate_designation=candidate_designation or "(unspecified)",
            candidate_experience=candidate_experience or "(unspecified)",
            required_experience=required_experience
            or "(not specified — use the experience stated in the role profile, else the candidate's experience)",
            resume_text=_truncate(
                resume_text or "(no resume text available)",
                _RESUME_CONTEXT_CHAR_LIMIT,
            ),
            target_label=target_label,
            role_profile=_truncate(role_profile, _JD_CONTEXT_CHAR_LIMIT),
            transcript=transcript_block,
        )
        raw = await self._llm.complete_json(
            [
                ChatMessage(role="system", content=system_text),
                ChatMessage(role="user", content=user_text),
            ]
        )
        return self._parse(raw, ROLE_EVALUATOR_VERSION)

    def _format_transcript(self, transcript: list[TranscriptEntry]) -> str:
        if not transcript:
            # Shouldn't normally happen — a submitted session has at least one
            # question — but be defensive so the evaluator still runs.
            return "(no transcript)"
        blocks: list[str] = []
        for entry in transcript:
            answer = (entry.answer_text or "(no answer submitted)").strip()
            expected = (entry.expected_answer or "(none)").strip()
            rubric = (entry.evaluation_rubric or "(none)").strip()
            block = (
                f"Q{entry.question_number} [{entry.question_type}]: "
                f"{entry.question_text.strip()}\n"
                f"Candidate answer: {answer}\n"
                f"Expected answer: {expected}\n"
                f"Rubric: {rubric}"
            )
            blocks.append(block)
        joined = "\n\n---\n\n".join(blocks)
        return _truncate(joined, _TRANSCRIPT_CHAR_LIMIT)

    def _parse(self, raw: dict[str, Any], prompt_version: str) -> EvaluationResult:
        try:
            overall = _clamp_score(raw.get("overall_score"))
            technical = _clamp_score(raw.get("technical_score"))
            communication = _clamp_score(raw.get("communication_score"))
            problem_solving = _clamp_score(raw.get("problem_solving_score"))
            project_knowledge = _clamp_score(raw.get("project_knowledge_score"))
            verdict = str(raw.get("ai_verdict") or "").upper()
            if verdict not in _ALLOWED_VERDICTS:
                logger.warning(
                    "Evaluator returned unexpected verdict %r; coercing to BORDERLINE",
                    verdict,
                )
                verdict = "BORDERLINE"
            confidence_raw = raw.get("confidence")
            confidence = (
                _clamp(Decimal(str(confidence_raw)), Decimal("0"), Decimal("1"))
                if confidence_raw is not None
                else Decimal("0.5")
            )
            summary = str(raw.get("summary") or "").strip()
            strengths = _clean_string_list(raw.get("strengths"))
            weaknesses = _clean_string_list(raw.get("weaknesses"))
            improvements = _clean_string_list(raw.get("improvement_areas"))
            skill_scores = _parse_skill_scores(raw.get("skill_scores") or [])
        except (TypeError, ValueError, ArithmeticError) as exc:
            logger.error("Evaluator LLM response parse failure: %s | raw=%r", exc, raw)
            raise LLMError(
                "Evaluator returned an unparseable response."
            ) from exc

        return EvaluationResult(
            overall_score=overall,
            technical_score=technical,
            communication_score=communication,
            reasoning_score=problem_solving,
            project_knowledge_score=project_knowledge,
            ai_verdict=verdict,
            confidence=confidence,
            summary=summary,
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_areas=improvements,
            skill_scores=skill_scores,
            prompt_version=prompt_version,
            model_name="",  # filled in by lifecycle service
        )


def _clamp_score(value: Any) -> Decimal:
    """Coerce ``value`` to a Decimal in [0, 10]. Missing → 0."""
    if value is None:
        return Decimal("0")
    return _clamp(Decimal(str(value)), Decimal("0"), Decimal("10"))


def _clamp(value: Decimal, lo: Decimal, hi: Decimal) -> Decimal:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _clean_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _parse_skill_scores(items: Any) -> list[SkillScoreResult]:
    if not isinstance(items, list):
        return []
    out: list[SkillScoreResult] = []
    seen_names: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_name = item.get("skill_name")
        if not isinstance(raw_name, str):
            continue
        name = raw_name.strip()[:150]
        if not name:
            continue
        normalized_name = name.casefold()
        if normalized_name in seen_names:
            continue
        try:
            score = _clamp_score(item.get("score"))
        except (TypeError, ValueError, ArithmeticError):
            continue
        seen_names.add(normalized_name)
        strength_raw = item.get("strength")
        strength = strength_raw.strip() if isinstance(strength_raw, str) and strength_raw.strip() else None
        improvement_raw = item.get("improvement_area")
        improvement = (
            improvement_raw.strip()
            if isinstance(improvement_raw, str) and improvement_raw.strip()
            else None
        )
        evidence = _clean_string_list(item.get("evidence"))
        out.append(
            SkillScoreResult(
                skill_name=name,
                score=score,
                strength=strength,
                improvement_area=improvement,
                evidence=evidence,
            )
        )
    return out


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... (truncated)"
