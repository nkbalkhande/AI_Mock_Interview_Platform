"""Question planner prompt for a specific vacancy job description."""

from app.ai.prompts.base import PromptTemplate
from app.ai.prompts.question_planner_base import (
    SHARED_SYSTEM_MECHANICS,
    SHARED_USER_INSTRUCTIONS,
    SHARED_USER_SESSION_CONTEXT,
)

JD_QUESTION_PLANNER_VERSION = "jd_question_planner_v1"

_SYSTEM = (
    """You are an expert technical interviewer assessing a candidate for a
specific vacancy described by a job description.

JD-SPECIFIC ASSESSMENT:
- Extract and prioritize the vacancy's required and preferred skills.
- Assess the stated responsibilities and likely day-to-day work.
- Test resume-to-JD alignment with concrete evidence, not keyword overlap.
- Probe resume claims that matter to this specific vacancy.
- Spend limited time on the highest-priority JD gaps and responsibilities.
- Keep questions grounded in this vacancy; do not broaden the assessment into
  a generic role competency survey.
"""
    + SHARED_SYSTEM_MECHANICS
)

_USER = (
    SHARED_USER_SESSION_CONTEXT
    + """

Specific vacancy job description:
\"\"\"
{target_context}
\"\"\"
"""
    + SHARED_USER_INSTRUCTIONS
)

JD_QUESTION_PLANNER_PROMPT = PromptTemplate(
    version=JD_QUESTION_PLANNER_VERSION,
    system=_SYSTEM,
    user_template=_USER,
)
