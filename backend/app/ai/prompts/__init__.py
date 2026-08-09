"""Prompt registry.

Every prompt is a small pure Python object (``PromptTemplate``) so that:

- Its ``version`` string can be persisted alongside evaluation rows for audit
  and re-run (see ``interview_evaluations.prompt_version``).
- Rendering is deterministic given the same variables.
- Unit tests can render + assert prompts without touching an LLM.

Version strings follow ``<slug>_v<n>``; bump the version whenever the prompt
text changes materially so historical evaluations remain re-runnable against
the exact prompt they were generated with.
"""

from app.ai.prompts.base import PromptTemplate
from app.ai.prompts.evaluator_jd import (
    JD_EVALUATOR_PROMPT,
    JD_EVALUATOR_VERSION,
)
from app.ai.prompts.evaluator_role import (
    ROLE_EVALUATOR_PROMPT,
    ROLE_EVALUATOR_VERSION,
)
from app.ai.prompts.question_planner_jd import (
    JD_QUESTION_PLANNER_PROMPT,
    JD_QUESTION_PLANNER_VERSION,
)
from app.ai.prompts.question_planner_role import (
    ROLE_QUESTION_PLANNER_PROMPT,
    ROLE_QUESTION_PLANNER_VERSION,
)

__all__ = [
    "PromptTemplate",
    "JD_EVALUATOR_PROMPT",
    "JD_EVALUATOR_VERSION",
    "ROLE_EVALUATOR_PROMPT",
    "ROLE_EVALUATOR_VERSION",
    "JD_QUESTION_PLANNER_PROMPT",
    "JD_QUESTION_PLANNER_VERSION",
    "ROLE_QUESTION_PLANNER_PROMPT",
    "ROLE_QUESTION_PLANNER_VERSION",
]
