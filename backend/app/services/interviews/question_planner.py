"""Adaptive question generator for JD-based practice interviews (v2).

Design change from v1:

- No pre-computed plan is passed in. The LLM decides which STAGE the next
  question belongs to based on interview duration, elapsed/remaining time,
  a lightweight coverage state, the JD, resume, and prior answers.
- The planner returns both a STAGE (LLM's interview-flow decision) and a
  DB-legal ``question_type`` derived from that stage (see ``_STAGE_TO_TYPE``).
  Callers persist the true stage in ``question_metadata`` for reproducibility
  while the DB row's ``question_type`` stays inside the CHECK constraint.
- The lifecycle service owns termination: once we've asked
  ``total_target_questions`` OR the planner emits ``stage=CLOSING``, no
  further planner calls are made.

The class is intentionally still *thin*: prompt render → ``ChatLLM.complete_json``
→ validate → return dataclass. State and transactions live one layer up.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from app.ai.llm.chat import ChatLLM, ChatMessage, LLMError
from app.ai.prompts import (
    JD_QUESTION_PLANNER_PROMPT,
    ROLE_QUESTION_PLANNER_PROMPT,
)
from app.ai.prompts.base import PromptTemplate
from app.core.logging import get_logger

logger = get_logger(__name__)

_ALLOWED_STAGES: tuple[str, ...] = (
    "INTRODUCTION",
    "TECHNICAL",
    "PROJECT",
    "CODING",
    "BEHAVIORAL",
    "CLOSING",
)
_ALLOWED_DIFFICULTIES = {"EASY", "MEDIUM", "HARD"}

# Map planner-chosen stages onto values that survive the DB's
# ``interview_questions.question_type`` CHECK constraint. INTRODUCTION /
# CLOSING don't have a first-class column value, so they ride along as
# BEHAVIORAL — the true stage is preserved in ``question_metadata.stage``.
_STAGE_TO_TYPE: dict[str, str] = {
    "INTRODUCTION": "BEHAVIORAL",
    "TECHNICAL": "TECHNICAL",
    "PROJECT": "PROJECT",
    "CODING": "CODING",
    "BEHAVIORAL": "BEHAVIORAL",
    "CLOSING": "BEHAVIORAL",
}

# Cap resume/JD text going into the prompt so we don't blow past model context
# on a huge resume or JD paste. 6000 chars is ~1500 tokens — comfortable for
# gpt-4o-mini and leaves headroom for the history block.
_RESUME_CONTEXT_CHAR_LIMIT = 6000
_TARGET_CONTEXT_CHAR_LIMIT = 6000
_ANSWER_HISTORY_CHAR_LIMIT = 800


@dataclass(frozen=True)
class PlannedQuestion:
    question_text: str
    question_type: str  # DB-legal type (mapped from stage)
    stage: str  # LLM-chosen interview stage
    difficulty: str
    topic: str
    skill: str
    expected_answer: str
    evaluation_rubric: str
    prompt_version: str
    model_name: str


@dataclass(frozen=True)
class AnswerSnapshot:
    """Prior Q&A pair passed into the planner as history."""

    question_number: int
    question_type: str
    question_text: str
    answer_text: str | None
    stage: str | None = None  # persisted from prior planner turns when known


@dataclass(frozen=True)
class TargetContext:
    """Immutable interview target rendered from either a JD or role snapshot."""

    kind: str
    label: str
    content: str


class JdQuestionPlanner:
    """Shared planner orchestration with mode-specific prompt dispatch."""

    def __init__(self, llm: ChatLLM) -> None:
        self._llm = llm

    async def plan_next(
        self,
        *,
        question_number: int,
        total_target_questions: int,
        interview_duration_minutes: int,
        elapsed_time_minutes: float,
        remaining_time_minutes: float,
        target_context: TargetContext,
        resume_text: str | None,
        candidate_designation: str | None,
        candidate_experience: str | None,
        coverage: dict[str, Any] | None,
        history: list[AnswerSnapshot],
    ) -> PlannedQuestion:
        history_block = self._format_history(history)
        coverage_block = _format_coverage(coverage or {})
        prompt = _prompt_for_target(target_context)

        user_prompt_variables: dict[str, Any] = {
            "interview_duration_minutes": interview_duration_minutes,
            "elapsed_time_minutes": _fmt_minutes(elapsed_time_minutes),
            "remaining_time_minutes": _fmt_minutes(remaining_time_minutes),
            "question_number": question_number,
            "total_target_questions": total_target_questions,
            "target_label": target_context.label,
            "target_context": _truncate(
                target_context.content, _TARGET_CONTEXT_CHAR_LIMIT
            ),
            "resume_text": _truncate(
                resume_text or "(no resume text available)",
                _RESUME_CONTEXT_CHAR_LIMIT,
            ),
            "candidate_designation": candidate_designation or "(unspecified)",
            "candidate_experience": candidate_experience or "(unspecified)",
            "coverage_summary": coverage_block,
            "history": history_block,
        }
        system_text, user_text = prompt.render(
            **user_prompt_variables
        )

        raw = await self._llm.complete_json(
            [
                ChatMessage(role="system", content=system_text),
                ChatMessage(role="user", content=user_text),
            ]
        )
        planned = self._parse(raw, prompt_version=prompt.version)
        if question_number == 1 and planned.stage != "INTRODUCTION":
            logger.warning(
                "Planner returned %s for question one; enforcing INTRODUCTION",
                planned.stage,
            )
            planned = replace(
                planned,
                question_text=(
                    "To start, please introduce yourself and summarize your "
                    "background and experience most relevant to this opportunity."
                ),
                question_type=_STAGE_TO_TYPE["INTRODUCTION"],
                stage="INTRODUCTION",
                difficulty="EASY",
                topic="introduction",
                skill="communication",
                expected_answer=(
                    "A concise summary of relevant experience, responsibilities, "
                    "and motivation for the role."
                ),
                evaluation_rubric=(
                    "Strong answers are clear, concise, and connect the candidate's "
                    "experience to the interview target."
                ),
            )
        return planned

    def _format_history(self, history: list[AnswerSnapshot]) -> str:
        if not history:
            return "(none — this is the first question)"
        lines: list[str] = []
        for item in history:
            answer = (item.answer_text or "(no answer submitted)").strip()
            answer = _truncate(answer, _ANSWER_HISTORY_CHAR_LIMIT)
            stage_hint = f" ({item.stage})" if item.stage else ""
            lines.append(
                f"Q{item.question_number} [{item.question_type}{stage_hint}]: "
                f"{item.question_text.strip()}\n"
                f"A{item.question_number}: {answer}"
            )
        return "\n\n".join(lines)

    def _parse(
        self, raw: dict[str, Any], *, prompt_version: str
    ) -> PlannedQuestion:
        try:
            question_text = str(raw["question_text"]).strip()
            topic = str(raw.get("topic") or "").strip()
            skill = str(raw.get("skill") or "").strip()
            difficulty = str(raw.get("difficulty") or "MEDIUM").upper()
            stage = str(raw.get("stage") or "").upper()
            expected_answer = str(raw.get("expected_answer") or "").strip()
            evaluation_rubric = str(raw.get("evaluation_rubric") or "").strip()
        except KeyError as exc:
            logger.error("Planner LLM response missing key: %s | raw=%r", exc, raw)
            raise LLMError(
                "Question planner returned an unexpected shape."
            ) from exc

        if not question_text:
            raise LLMError("Question planner returned an empty question.")

        if stage not in _ALLOWED_STAGES:
            logger.warning(
                "Planner returned unexpected stage %r; coercing to TECHNICAL",
                stage,
            )
            stage = "TECHNICAL"

        if difficulty not in _ALLOWED_DIFFICULTIES:
            # Coerce to MEDIUM rather than fail the interview loop over a
            # stray label — the DB column is only informational for practice.
            logger.warning(
                "Planner returned unexpected difficulty %r; coercing to MEDIUM",
                difficulty,
            )
            difficulty = "MEDIUM"

        db_type = _STAGE_TO_TYPE[stage]

        return PlannedQuestion(
            question_text=question_text,
            question_type=db_type,
            stage=stage,
            difficulty=difficulty,
            topic=topic[:150],
            skill=skill[:150],
            expected_answer=expected_answer,
            evaluation_rubric=evaluation_rubric,
            prompt_version=prompt_version,
            model_name="",  # filled in by lifecycle service (has settings.OPENAI_MODEL)
        )


# ---------------------- module helpers ----------------------


def _prompt_for_target(target_context: TargetContext) -> PromptTemplate:
    if target_context.kind == "JD":
        return JD_QUESTION_PLANNER_PROMPT
    if target_context.kind == "ROLE":
        return ROLE_QUESTION_PLANNER_PROMPT
    raise ValueError(
        f"Unsupported target context kind: {target_context.kind!r}. "
        "Expected 'JD' or 'ROLE'."
    )


def _format_coverage(coverage: dict[str, Any]) -> str:
    """Render the coverage dict as a compact, human-readable block.

    Kept deterministic and small: the LLM works better with a short bullet
    list than a JSON blob.
    """
    if not coverage:
        return "(no coverage yet — this is the beginning of the interview)"

    def _yn(v: object) -> str:
        return "yes" if bool(v) else "no"

    lines: list[str] = []
    lines.append(f"- Introduction completed: {_yn(coverage.get('introduction_completed'))}")
    topics = coverage.get("technical_topics") or []
    if isinstance(topics, list) and topics:
        lines.append(
            "- Technical topics covered: " + ", ".join(str(t) for t in topics[:20])
        )
    else:
        lines.append("- Technical topics covered: (none yet)")
    lines.append(f"- Project discussed: {_yn(coverage.get('project_discussed'))}")
    lines.append(f"- Coding completed: {_yn(coverage.get('coding_completed'))}")
    lines.append(f"- Behavioral completed: {_yn(coverage.get('behavioral_completed'))}")
    lines.append(f"- Closing completed: {_yn(coverage.get('closing_completed'))}")

    tech_count = coverage.get("technical_count")
    if isinstance(tech_count, int) and tech_count > 0:
        lines.append(f"- Technical questions asked so far: {tech_count}")

    return "\n".join(lines)


def _fmt_minutes(value: float | int) -> str:
    """Format a minute value for the prompt (integer when close, else 1 dp)."""
    v = float(value)
    if v < 0:
        v = 0.0
    if abs(v - round(v)) < 0.05:
        return str(int(round(v)))
    return f"{v:.1f}"


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... (truncated)"
