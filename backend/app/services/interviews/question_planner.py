"""Adaptive question generator for JD-based practice interviews (v2).

Design change from v1:

- No pre-computed plan is passed in. The LLM decides which STAGE the next
  question belongs to based on interview duration, elapsed/remaining time,
  a lightweight coverage state, the JD, resume, and prior answers.
- The planner returns both a STAGE (LLM's interview-flow decision) and a
  DB-legal ``question_type`` derived from that stage (see ``_STAGE_TO_TYPE``).
  Callers persist the true stage in ``question_metadata`` for reproducibility
  while the DB row's ``question_type`` stays inside the CHECK constraint.
- The last planned question is always CLOSING (deterministic wrap-up).
  The lifecycle service then stops: no further planner calls after
  ``stage=CLOSING`` or ``total_target_questions``.

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
_ANSWER_HISTORY_CHAR_LIMIT = 1500
_LATEST_ANSWER_CHAR_LIMIT = 2500

INTRODUCTION_FALLBACK_QUESTION = (
    "Could you briefly walk me through your background and the experience "
    "most relevant to this role?"
)

CLOSING_FALLBACK_QUESTION = (
    "Before we wrap up, is there anything else about your experience "
    "for this role that we haven't covered and you'd like me to consider?"
)

# If remaining time is at or below this, skip further content probes and close.
_CLOSING_REMAINING_MINUTES = 2.0


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
        prompt = _prompt_for_target(target_context)
        if _should_close(
            question_number=question_number,
            total_target_questions=total_target_questions,
            remaining_time_minutes=remaining_time_minutes,
        ):
            return _forced_closing(prompt_version=prompt.version)

        history_block = self._format_history(history)
        latest_answer_block = _format_latest_answer(history)
        coverage_block = _format_coverage(coverage or {})
        mix_block = _mix_guidance(
            question_number=question_number,
            total_target_questions=total_target_questions,
            interview_duration_minutes=interview_duration_minutes,
            history=history,
            coverage=coverage or {},
        )
        budget_block = _duration_budget(
            interview_duration_minutes=interview_duration_minutes,
            elapsed_time_minutes=elapsed_time_minutes,
        )

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
            "mix_guidance": mix_block,
            "duration_budget": budget_block,
            "history": history_block,
            "latest_answer": latest_answer_block,
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
                question_text=INTRODUCTION_FALLBACK_QUESTION,
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
            model_name="",  # filled in by lifecycle service (has settings.llm.model)
        )


# ---------------------- module helpers ----------------------


def _should_close(
    *,
    question_number: int,
    total_target_questions: int,
    remaining_time_minutes: float,
) -> bool:
    """Last planned slot, or almost no time left, must be a wrap-up."""
    if question_number <= 1:
        return False
    if question_number >= total_target_questions:
        return True
    return float(remaining_time_minutes) <= _CLOSING_REMAINING_MINUTES


def _forced_closing(*, prompt_version: str) -> PlannedQuestion:
    return PlannedQuestion(
        question_text=CLOSING_FALLBACK_QUESTION,
        question_type=_STAGE_TO_TYPE["CLOSING"],
        stage="CLOSING",
        difficulty="EASY",
        topic="closing",
        skill="communication",
        expected_answer=(
            "A concise addition of relevant experience not yet covered, "
            "or a clear statement that nothing further needs to be added."
        ),
        evaluation_rubric=(
            "Strong answers add specific, role-relevant evidence or close "
            "cleanly. Weak answers ramble, repeat earlier points, or go off-topic."
        ),
        prompt_version=prompt_version,
        model_name="",
    )


def _prompt_for_target(target_context: TargetContext) -> PromptTemplate:
    if target_context.kind == "JD":
        return JD_QUESTION_PLANNER_PROMPT
    if target_context.kind == "ROLE":
        return ROLE_QUESTION_PLANNER_PROMPT
    raise ValueError(
        f"Unsupported target context kind: {target_context.kind!r}. "
        "Expected 'JD' or 'ROLE'."
    )


def _as_count(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _history_stage(item: AnswerSnapshot) -> str:
    """Prefer planner stage; fall back to persisted question_type."""
    if item.stage:
        return item.stage.upper()
    return (item.question_type or "").upper()


# Category quota tiers, selected in Python at prompt-assembly time so the
# LLM never has to read the duration and self-select the right tier.
# (min, max) counts per category; SKILL renders as stage TECHNICAL.
_TIER_15: dict[str, Any] = {
    "label": "15 MINUTES — screening pass",
    "target": "7-8",
    "project": (2, 3),
    "skill": (3, 4),
    "coding": (1, 1),
    "behavioral": (0, 0),
    "coding_note": (
        "1 CODING — mandatory, cannot be dropped for any reason; one "
        "bounded practical problem (DIFFICULTY CEILING applies)."
    ),
}
_TIER_30: dict[str, Any] = {
    "label": "30 MINUTES",
    "target": "13-14",
    "project": (3, 4),
    "skill": (5, 6),
    "coding": (1, 2),
    "behavioral": (0, 0),
    "coding_note": "1-2 CODING — mandatory, at least 1.",
}
_TIER_45: dict[str, Any] = {
    "label": "45 MINUTES",
    "target": "14-15",
    "project": (2, 3),
    "skill": (5, 6),
    "coding": (1, 1),
    "behavioral": (0, 2),
    "coding_note": "1 CODING — mandatory.",
    "behavioral_note": (
        "1-2 BEHAVIORAL — weight toward candidates who read as "
        "senior/lead from their introduction and experience level (broad "
        "ownership, mentoring, cross-team decisions). For an "
        "early-career candidate (~0-2 years), reduce to 0-1 BEHAVIORAL "
        "and reallocate that slot to SKILL or PROJECT instead."
    ),
}
_TIER_60: dict[str, Any] = {
    "label": "60 MINUTES",
    "target": "14-15",
    "project": (2, 3),
    "skill": (3, 4),
    "coding": (1, 2),
    "behavioral": (0, 0),
    "coding_note": (
        "1-2 CODING — mandatory, at least 1. Unlike shorter durations, "
        "give the coding portion real room: pose a LeetCode "
        "MEDIUM-to-HARD level problem (scaled down only if the "
        "DIFFICULTY CEILING caps it for a low-experience candidate), "
        "and allow follow-up on approach, complexity, and edge cases "
        "rather than treating it as a single quick exchange. This is "
        "why the total question count stays similar to 45 minutes — "
        "the coding slot absorbs the extra minutes, not more questions "
        "elsewhere."
    ),
}


def _budget_tier(duration: int) -> dict[str, Any]:
    if duration <= 15:
        return _TIER_15
    if duration <= 30:
        return _TIER_30
    if duration <= 45:
        return _TIER_45
    return _TIER_60


def _fmt_range(bounds: tuple[int, int]) -> str:
    low, high = bounds
    return str(low) if low == high else f"{low}-{high}"


def _duration_budget(
    *,
    interview_duration_minutes: int,
    elapsed_time_minutes: float,
) -> str:
    """Render the category-quota allocation for this interview's duration.

    The tier is picked here, in Python, so the prompt only ever contains
    the one allocation that applies — the LLM does not self-select.
    """
    duration = max(1, int(interview_duration_minutes))
    tier = _budget_tier(duration)
    elapsed = max(0.0, float(elapsed_time_minutes))

    lines: list[str] = [
        f"Allocation: {tier['label']} (target {tier['target']} questions "
        f"for this {duration}-minute interview):",
        "- 1 INTRODUCTION",
        (
            f"- {_fmt_range(tier['project'])} PROJECT — if the resume "
            "lists 2+ projects, ask on at least 2 of them rather than "
            "concentrating all project questions on one"
        ),
        (
            f"- {_fmt_range(tier['skill'])} SKILL (stage TECHNICAL) — "
            "each question must target a DIFFERENT resume skill; never "
            "two SKILL questions on the same skill/technology"
        ),
        f"- {tier['coding_note']}",
    ]
    if tier["behavioral"][1] > 0:
        lines.append(f"- {tier['behavioral_note']}")
    lines.append(
        "- 1 CLOSING — only if time remains after the above; skip it if "
        "the interview is out of time rather than cutting a mandatory "
        "category"
    )
    lines.extend(
        [
            "Shared rules:",
            "- Every CODING question follows CODING QUESTION FORMAT "
            "(description + input/output example) without exception.",
            "- SKILL questions must not repeat a skill already asked. If "
            "the resume runs out of distinct relevant skills before the "
            "quota is filled, use the remaining slots for additional "
            "PROJECT depth instead of repeating a skill.",
            "- PROJECT still respects the THREAD CAP (max 3 consecutive "
            "questions on one single project) even when the overall "
            "PROJECT quota is higher — spread across projects rather "
            "than stacking depth on one.",
            "- If a mandatory category (CODING; PROJECT coverage of 2+ "
            "projects when they exist) is not yet satisfied and the "
            "remaining time/question budget is running out, it takes "
            "priority over CLOSING and over additional SKILL questions.",
            "- CLOSING is the only fully optional category — every other "
            "category's minimum must be met first if time allows.",
            f"Elapsed {elapsed:.0f} of {duration} minutes.",
        ]
    )
    return "\n".join(lines)


def _mix_guidance(
    *,
    question_number: int,
    total_target_questions: int,
    interview_duration_minutes: int,
    history: list[AnswerSnapshot],
    coverage: dict[str, Any],
) -> str:
    """Hard constraints so one project cannot consume the interview.

    Prompt text alone was not enough: the model followed the named-work
    thread through contribution → hardest part → evaluation → outage →
    triage. This block is injected into the user prompt each turn as a
    deterministic safety net under the DURATION BUDGET's category quotas.
    """
    if question_number <= 1:
        return (
            "Ask an open introduction. Do not steer toward a skill, "
            "project, or technology."
        )

    duration = max(1, int(interview_duration_minutes))
    tier = _budget_tier(duration)
    stages = [_history_stage(item) for item in history]
    project_n = sum(1 for stage in stages if stage == "PROJECT")
    technical_n = sum(1 for stage in stages if stage == "TECHNICAL")
    coding_n = sum(1 for stage in stages if stage == "CODING")
    project_n = max(project_n, _as_count(coverage.get("project_count")))
    technical_n = max(technical_n, _as_count(coverage.get("technical_count")))
    if coverage.get("coding_completed"):
        coding_n = max(coding_n, 1)

    consecutive_project = 0
    for stage in reversed(stages):
        if stage == "PROJECT":
            consecutive_project += 1
            continue
        if stage in {"INTRODUCTION", "BEHAVIORAL"}:
            continue
        break

    max_project: int = tier["project"][1]
    max_skill: int = tier["skill"][1]
    min_coding: int = tier["coding"][0]
    consecutive_cap = 3  # THREAD CAP: max 3 in a row on one project.

    content_including_this = max(0, total_target_questions - question_number)

    lines = [
        (
            f"Asked so far: {project_n} PROJECT (quota "
            f"{_fmt_range(tier['project'])}), {technical_n} SKILL/TECHNICAL "
            f"(quota {_fmt_range(tier['skill'])}), {coding_n} CODING "
            f"(mandatory, quota {_fmt_range(tier['coding'])})."
        ),
        (
            "Content questions remaining (including this, excluding closing): "
            f"{content_including_this}."
        ),
    ]
    topics = coverage.get("technical_topics") or []
    if isinstance(topics, list) and topics:
        asked = ", ".join(str(t) for t in topics[:20] if str(t).strip())
        if asked:
            lines.append(
                f"Skills/topics already asked — a SKILL question must "
                f"target a DIFFERENT resume skill: {asked}."
            )

    required: str | None = None
    if coding_n < min_coding and content_including_this <= 2:
        # Last-chance window: mandatory coding takes priority over more
        # SKILL questions and over CLOSING.
        required = "CODING"
    elif project_n >= max_project:
        if coding_n < min_coding:
            required = "CODING"
        elif technical_n == 0:
            required = "TECHNICAL"
        else:
            required = "NOT_PROJECT"
    elif consecutive_project >= consecutive_cap:
        required = "NEW_PROJECT_ONLY"
    elif technical_n >= max_skill and coding_n >= min_coding:
        required = "NOT_SKILL"
    elif technical_n == 0 and content_including_this <= 1:
        required = "TECHNICAL"

    if required == "CODING":
        lines.append(
            "HARD RULE: stage MUST be CODING. Pose it per CODING QUESTION "
            "FORMAT: a brief problem description PLUS a sample input and "
            "expected output. Scope it to the candidate's experience "
            "(DIFFICULTY CEILING). Do not ask another project-story "
            "question."
        )
    elif required == "TECHNICAL":
        lines.append(
            "HARD RULE: stage MUST be TECHNICAL. Ask a SKILL question on "
            "a resume skill not yet covered (how it works, architecture, "
            "algorithms, evaluation method, trade-offs). Do NOT ask "
            "another biography question (contribution, hardest part, what "
            "broke, who owned what, first signal you checked)."
        )
    elif required == "NOT_PROJECT":
        lines.append(
            "HARD RULE: stage MUST NOT be PROJECT — the PROJECT quota is "
            "spent. Choose a SKILL (TECHNICAL) question on a new resume "
            "skill, CODING if its quota allows another, or BEHAVIORAL if "
            "the DURATION BUDGET allocates it. Project storytelling is "
            "finished."
        )
    elif required == "NEW_PROJECT_ONLY":
        lines.append(
            "HARD RULE: the THREAD CAP is reached — 3 consecutive "
            "questions on this project. If the next question is PROJECT, "
            "it MUST target a DIFFERENT project from the resume. "
            "Otherwise switch to a SKILL or CODING question."
        )
    elif required == "NOT_SKILL":
        lines.append(
            "HARD RULE: the SKILL quota is spent. Choose PROJECT (within "
            "its quota and the THREAD CAP), CODING, or BEHAVIORAL per the "
            "DURATION BUDGET — not another SKILL question."
        )
    else:
        remaining_project = max(0, max_project - project_n)
        lines.append(
            f"You may ask a PROJECT question ({remaining_project} left in "
            "the quota) — one unused dimension, max 3 in a row on one "
            "project — or a SKILL question on a new resume skill, or the "
            "CODING question. Follow the DURATION BUDGET."
        )

    return "\n".join(lines)


def _format_latest_answer(history: list[AnswerSnapshot]) -> str:
    """Highlight the latest answer as the primary next-question input."""
    if not history:
        return (
            "(none — this is the first question. Ask an open introduction "
            "that lets the candidate choose the experience most relevant to "
            "the role. Do not steer them toward a specific skill.)"
        )
    item = history[-1]
    answer = (item.answer_text or "(no answer submitted)").strip()
    answer = _truncate(answer, _LATEST_ANSWER_CHAR_LIMIT)
    already_asked = "\n".join(
        f"- Q{h.question_number}: {h.question_text.strip()}" for h in history
    )
    return (
        f"Previous question: {item.question_text.strip()}\n"
        f"Candidate's latest answer:\n{answer}\n\n"
        "Decide the next question from this answer first. "
        "Follow the thread unless the evidence-mix constraints forbid "
        "another PROJECT question, or another listed exception applies.\n\n"
        "Questions already asked — do not repeat or paraphrase any of these:\n"
        f"{already_asked}"
    )


def _format_coverage(coverage: dict[str, Any]) -> str:
    """Render evidence already collected — never a remaining-stage checklist.

    Listing unvisited stages as "no" caused the planner to fill Project,
    Behavioral, then Coding instead of following the candidate's answer.
    """
    explored: list[str] = []
    if coverage.get("introduction_completed"):
        explored.append("introduction")
    topics = coverage.get("technical_topics") or []
    if isinstance(topics, list):
        explored.extend(str(topic) for topic in topics[:20] if str(topic).strip())
    if coverage.get("project_discussed"):
        explored.append("a project/experience thread")
    if coverage.get("coding_completed"):
        explored.append("coding/problem-solving")
    if coverage.get("behavioral_completed"):
        explored.append("behavioral/judgment")
    if coverage.get("closing_completed"):
        explored.append("closing")

    lines = [
        "This is a record of what has already been discussed.",
        "It is NOT a checklist of remaining stages to visit.",
        "Do not switch topics merely because a stage or competency is absent.",
        "Do obey the evidence-mix constraints when they forbid another PROJECT question.",
    ]
    if explored:
        lines.append("- Already explored: " + ", ".join(explored))
    else:
        lines.append("- Already explored: (nothing yet)")

    tech_count = coverage.get("technical_count")
    if isinstance(tech_count, int) and tech_count > 0:
        lines.append(f"- Technical questions asked so far: {tech_count}")
    project_count = coverage.get("project_count")
    if isinstance(project_count, int) and project_count > 0:
        lines.append(f"- Project questions asked so far: {project_count}")

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
