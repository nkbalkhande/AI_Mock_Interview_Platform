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
    CLOSING_FALLBACK_QUESTION,
    AnswerSnapshot,
    JdQuestionPlanner,
    TargetContext,
    _duration_budget,
    _mix_guidance,
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
async def test_planner_forces_last_question_to_closing() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Describe how you measured hybrid retrieval.",
            "topic": "evaluation",
            "skill": "metrics",
            "difficulty": "HARD",
            "stage": "TECHNICAL",
            "expected_answer": "Precision, recall, human eval.",
            "evaluation_rubric": "Strong: names a metric and a baseline.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(
        **_plan_kwargs(
            question_number=5,
            total_target_questions=5,
            elapsed_time_minutes=12.0,
            remaining_time_minutes=3.0,
        )
    )

    assert result.stage == "CLOSING"
    assert result.question_type == "BEHAVIORAL"
    assert result.question_text == CLOSING_FALLBACK_QUESTION
    assert llm.messages == []


@pytest.mark.asyncio
async def test_planner_closes_early_when_time_is_almost_gone() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Why that architecture?",
            "topic": "architecture",
            "skill": "judgment",
            "difficulty": "MEDIUM",
            "stage": "PROJECT",
            "expected_answer": "Trade-offs.",
            "evaluation_rubric": "Strong answers compare alternatives.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    result = await planner.plan_next(
        **_plan_kwargs(
            question_number=3,
            total_target_questions=5,
            elapsed_time_minutes=13.5,
            remaining_time_minutes=1.5,
        )
    )

    assert result.stage == "CLOSING"
    assert result.question_text == CLOSING_FALLBACK_QUESTION
    assert llm.messages == []


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
    assert "ROLE FOLLOW-THROUGH" in rendered
    assert "FOLLOW-UP CONTRACT" in rendered
    assert "JD FOLLOW-THROUGH" not in rendered
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
    assert "JD FOLLOW-THROUGH" in rendered
    assert "FOLLOW-UP CONTRACT" in rendered
    assert "ROLE FOLLOW-THROUGH" not in rendered
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
    assert result.question_text == (
        "Could you briefly walk me through your background and the experience "
        "most relevant to this role?"
    )


@pytest.mark.asyncio
async def test_planner_puts_latest_answer_before_resume() -> None:
    llm = _FakeLLM(
        {
            "question_text": "What was the hardest part of that forecasting work?",
            "topic": "forecasting",
            "skill": "applied ML",
            "difficulty": "MEDIUM",
            "stage": "PROJECT",
            "expected_answer": "A specific challenge and how they handled it.",
            "evaluation_rubric": "Strong answers show ownership and trade-offs.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]
    latest = (
        "I built a demand forecasting model that cut stockouts by 18 percent."
    )

    await planner.plan_next(
        **_plan_kwargs(
            question_number=2,
            resume_text="Solved 300 LeetCode problems. Built multi-agent systems.",
            coverage={
                "introduction_completed": True,
                "project_discussed": False,
                "coding_completed": False,
                "behavioral_completed": False,
                "closing_completed": False,
                "technical_topics": [],
                "technical_count": 0,
            },
            history=[
                AnswerSnapshot(
                    question_number=1,
                    question_type="BEHAVIORAL",
                    question_text="Walk me through your background.",
                    answer_text=latest,
                    stage="INTRODUCTION",
                )
            ],
        )
    )

    user_text = llm.messages[1].content
    assert user_text.index("LATEST CANDIDATE ANSWER") < user_text.index("Resume")
    assert user_text.index(latest) < user_text.index("Solved 300 LeetCode")
    assert "completed: no" not in user_text.lower()
    assert "Project discussed: no" not in user_text
    assert "Coding completed: no" not in user_text
    assert "Behavioral completed: no" not in user_text
    assert "NOT a checklist of remaining stages" in user_text
    assert "primary input for the next question" in user_text.lower()
    assert "do not repeat or paraphrase" in user_text.lower()
    assert "Walk me through your background." in user_text
    assert "This is question 2" not in user_text
    assert "Evidence mix for THIS question" in user_text
    assert "You may ask a PROJECT question" in user_text
    assert "DURATION BUDGET" in user_text


@pytest.mark.asyncio
async def test_planner_system_prompt_prioritizes_conversation_over_coverage() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Why did you choose that approach?",
            "topic": "decision making",
            "skill": "judgment",
            "difficulty": "MEDIUM",
            "stage": "PROJECT",
            "expected_answer": "Trade-offs and constraints.",
            "evaluation_rubric": "Strong answers compare alternatives.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    await planner.plan_next(**_plan_kwargs(question_number=2))

    system_text = llm.messages[0].content
    assert "competency checklist" in system_text.lower()
    assert "Do not pack multiple asks into one" in system_text
    assert "ANSWER ANCHORING" in system_text
    assert "INTERVIEWER VOICE" in system_text
    assert "FOLLOW-UP CONTRACT" in system_text
    assert "The last planned question MUST be CLOSING" in system_text
    assert "Progress naturally through introduction, technical" not in system_text
    assert "What do you work on day to day?" in system_text
    assert "A 30-minute interview (~13-14 questions) should look like:" in system_text
    assert "five questions about one project" in system_text.lower()
    assert "CODING QUESTION FORMAT" in system_text
    assert "THREAD CAP" in system_text
    assert "DIFFICULTY CEILING" in system_text
    user_text = llm.messages[1].content
    assert "Do not repeat or paraphrase any previous question" in user_text
    assert "You may ask a PROJECT question" in user_text
    assert "DURATION BUDGET" in user_text


@pytest.mark.asyncio
async def test_planner_forbids_paraphrasing_problem_statement_questions() -> None:
    llm = _FakeLLM(
        {
            "question_text": "What was the hardest part of getting that live?",
            "topic": "production",
            "skill": "ownership",
            "difficulty": "MEDIUM",
            "stage": "PROJECT",
            "expected_answer": "A specific production challenge.",
            "evaluation_rubric": "Strong answers show ownership.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    await planner.plan_next(
        **_plan_kwargs(
            question_number=4,
            history=[
                AnswerSnapshot(
                    question_number=1,
                    question_type="BEHAVIORAL",
                    question_text="Walk me through your background.",
                    answer_text="I lead a forecasting service at work.",
                    stage="INTRODUCTION",
                ),
                AnswerSnapshot(
                    question_number=2,
                    question_type="BEHAVIORAL",
                    question_text=(
                        "Could you start with your current role — "
                        "what do you work on day to day?"
                    ),
                    answer_text="I work on a demand forecasting model.",
                    stage="PROJECT",
                ),
                AnswerSnapshot(
                    question_number=3,
                    question_type="PROJECT",
                    question_text="What problem is your current project solving?",
                    answer_text="It predicts store-level demand.",
                    stage="PROJECT",
                ),
            ],
        )
    )

    user_text = llm.messages[1].content
    assert "What problem is your current project solving?" in user_text
    assert "do not repeat or paraphrase" in user_text.lower()
    assert "This is question 4" not in user_text
    assert "already asked what problem the work solves" not in user_text.lower()
    # Two project questions against the 30-minute quota of 3-4 leaves two.
    assert "You may ask a PROJECT question (2 left in the quota)" in user_text


def _intro_snapshot() -> AnswerSnapshot:
    return AnswerSnapshot(
        question_number=1,
        question_type="BEHAVIORAL",
        question_text="Walk me through your background.",
        answer_text="I built ASKNOVA, a multi-source AI knowledge assistant.",
        stage="INTRODUCTION",
    )


def _project_snapshot(number: int, question: str) -> AnswerSnapshot:
    return AnswerSnapshot(
        question_number=number,
        question_type="PROJECT",
        question_text=question,
        answer_text="I owned retrieval and evaluation on ASKNOVA.",
        stage="PROJECT",
    )


def _technical_snapshot(number: int) -> AnswerSnapshot:
    return AnswerSnapshot(
        question_number=number,
        question_type="TECHNICAL",
        question_text="How did ASKNOVA rank retrieved chunks?",
        answer_text="We used hybrid search plus a cross-encoder.",
        stage="TECHNICAL",
    )


def test_mix_guidance_allows_project_on_question_two() -> None:
    text = _mix_guidance(
        question_number=2,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[_intro_snapshot()],
        coverage={},
    )
    assert "HARD RULE" not in text
    assert "You may ask a PROJECT question" in text


def test_mix_guidance_allows_third_project_in_thirty_minutes() -> None:
    text = _mix_guidance(
        question_number=4,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[
            _intro_snapshot(),
            _project_snapshot(2, "What was your personal contribution?"),
            _project_snapshot(3, "What was the hardest part you owned?"),
        ],
        coverage={"project_count": 2, "technical_count": 0},
    )
    assert "HARD RULE" not in text
    assert "You may ask a PROJECT question (2 left in the quota)" in text


def test_mix_guidance_forces_coding_when_project_quota_spent() -> None:
    text = _mix_guidance(
        question_number=7,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[
            _intro_snapshot(),
            _project_snapshot(2, "What was your personal contribution?"),
            _project_snapshot(3, "What was the hardest part you owned?"),
            _technical_snapshot(4),
            _project_snapshot(5, "On the negotiation platform, what did you own?"),
            _project_snapshot(6, "Why agents instead of a single pipeline?"),
        ],
        coverage={"project_count": 4, "technical_count": 1},
    )
    assert "HARD RULE: stage MUST be CODING" in text


def test_mix_guidance_forces_coding_in_last_content_slots() -> None:
    text = _mix_guidance(
        question_number=13,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[
            _intro_snapshot(),
            _project_snapshot(2, "What was your personal contribution?"),
            _project_snapshot(3, "What was the hardest part you owned?"),
            _technical_snapshot(4),
        ],
        coverage={
            "project_count": 2,
            "technical_count": 1,
            "coding_completed": False,
        },
    )
    assert "HARD RULE: stage MUST be CODING" in text


def test_mix_guidance_thread_cap_requires_new_project() -> None:
    text = _mix_guidance(
        question_number=5,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[
            _intro_snapshot(),
            _project_snapshot(2, "What was your personal contribution?"),
            _project_snapshot(3, "What was the hardest part you owned?"),
            _project_snapshot(4, "Why that approach instead of alternatives?"),
        ],
        coverage={"project_count": 3, "technical_count": 0},
    )
    assert "THREAD CAP is reached" in text
    assert "MUST target a DIFFERENT project" in text


def test_mix_guidance_forces_technical_when_coding_done_and_quota_spent() -> None:
    coding = AnswerSnapshot(
        question_number=6,
        question_type="CODING",
        question_text="Write a function that deduplicates retrieved chunks.",
        answer_text="def dedupe(chunks): ...",
        stage="CODING",
    )
    text = _mix_guidance(
        question_number=7,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[
            _intro_snapshot(),
            _project_snapshot(2, "What was your personal contribution?"),
            _project_snapshot(3, "What was the hardest part you owned?"),
            _project_snapshot(4, "Why that approach instead of alternatives?"),
            _project_snapshot(5, "On the second project, what did you own?"),
            coding,
        ],
        coverage={
            "project_count": 4,
            "technical_count": 0,
            "coding_completed": True,
        },
    )
    assert "HARD RULE: stage MUST be TECHNICAL" in text


def test_mix_guidance_coding_is_mandatory_in_fifteen_minutes() -> None:
    text = _mix_guidance(
        question_number=7,
        total_target_questions=8,
        interview_duration_minutes=15,
        history=[
            _intro_snapshot(),
            _project_snapshot(2, "What was your personal contribution?"),
            _project_snapshot(3, "What was the hardest part you owned?"),
            _technical_snapshot(4),
        ],
        coverage={"project_count": 2, "technical_count": 1},
    )
    assert "HARD RULE: stage MUST be CODING" in text


def test_mix_guidance_blocks_skill_when_quota_spent() -> None:
    coding = AnswerSnapshot(
        question_number=8,
        question_type="CODING",
        question_text="Spot the bug in this retry decorator.",
        answer_text="The backoff never increments.",
        stage="CODING",
    )
    text = _mix_guidance(
        question_number=9,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[_intro_snapshot(), coding],
        coverage={"project_count": 1, "technical_count": 6},
    )
    assert "HARD RULE: the SKILL quota is spent" in text


def test_mix_guidance_lists_asked_skills_for_dedupe() -> None:
    text = _mix_guidance(
        question_number=5,
        total_target_questions=14,
        interview_duration_minutes=30,
        history=[_intro_snapshot(), _technical_snapshot(2)],
        coverage={
            "technical_count": 1,
            "technical_topics": ["hybrid retrieval", "Docker"],
        },
    )
    assert "target a DIFFERENT resume skill" in text
    assert "hybrid retrieval, Docker" in text


def test_duration_budget_thirty_lists_quotas() -> None:
    text = _duration_budget(
        interview_duration_minutes=30, elapsed_time_minutes=12.0
    )
    assert "target 13-14 questions" in text
    assert "- 3-4 PROJECT" in text
    assert "- 5-6 SKILL (stage TECHNICAL)" in text
    assert "1-2 CODING — mandatory, at least 1." in text
    assert "CODING QUESTION FORMAT" in text
    assert "CLOSING is the only fully optional category" in text
    assert "Elapsed 12 of 30 minutes." in text


def test_duration_budget_fifteen_keeps_coding_mandatory() -> None:
    text = _duration_budget(
        interview_duration_minutes=15, elapsed_time_minutes=0.0
    )
    assert "target 7-8 questions" in text
    assert "1 CODING — mandatory, cannot be dropped for any reason" in text
    assert "- 3-4 SKILL (stage TECHNICAL)" in text
    assert "BEHAVIORAL" not in text


def test_duration_budget_forty_five_weights_behavioral_by_seniority() -> None:
    text = _duration_budget(
        interview_duration_minutes=45, elapsed_time_minutes=0.0
    )
    assert "1-2 BEHAVIORAL" in text
    assert "early-career candidate (~0-2 years)" in text


def test_duration_budget_sixty_gives_coding_room() -> None:
    text = _duration_budget(
        interview_duration_minutes=60, elapsed_time_minutes=0.0
    )
    assert "MEDIUM-to-HARD" in text
    assert "the coding slot absorbs the extra minutes" in text
    assert "BEHAVIORAL" not in text


@pytest.mark.asyncio
async def test_planner_injects_coding_hard_rule_after_project_cap() -> None:
    llm = _FakeLLM(
        {
            "question_text": "Write a function that merges ranked result lists.",
            "topic": "implementation",
            "skill": "Python",
            "difficulty": "MEDIUM",
            "stage": "CODING",
            "expected_answer": "A working merge with tie-breaking.",
            "evaluation_rubric": "Strong answers handle duplicates and order.",
        }
    )
    planner = JdQuestionPlanner(llm)  # type: ignore[arg-type]

    await planner.plan_next(
        **_plan_kwargs(
            question_number=5,
            total_target_questions=7,
            target_context=TargetContext(
                kind="ROLE",
                label="AI Engineer",
                content="Build production AI systems. Python. RAG. Evaluation.",
            ),
            history=[
                _intro_snapshot(),
                _project_snapshot(2, "On ASKNOVA, what was your personal contribution?"),
                _project_snapshot(3, "On ASKNOVA, what was the hardest part?"),
                _project_snapshot(4, "On ASKNOVA, why that retrieval approach?"),
            ],
        )
    )

    user_text = llm.messages[1].content
    assert "Evidence mix for THIS question" in user_text
    assert "HARD RULE: stage MUST be CODING" in user_text
    assert "DURATION BUDGET" in user_text
    system_text = llm.messages[0].content
    assert "non-negotiable" in system_text
    assert "five questions about one project" in system_text.lower()
