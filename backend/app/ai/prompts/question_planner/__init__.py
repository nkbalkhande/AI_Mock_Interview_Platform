"""Question planner prompt package."""

from app.ai.prompts.question_planner.jd import (
    JD_QUESTION_PLANNER_PROMPT,
    JD_QUESTION_PLANNER_VERSION,
)
from app.ai.prompts.question_planner.role import (
    ROLE_QUESTION_PLANNER_PROMPT,
    ROLE_QUESTION_PLANNER_VERSION,
)

__all__ = [
    "JD_QUESTION_PLANNER_PROMPT",
    "JD_QUESTION_PLANNER_VERSION",
    "ROLE_QUESTION_PLANNER_PROMPT",
    "ROLE_QUESTION_PLANNER_VERSION",
]
