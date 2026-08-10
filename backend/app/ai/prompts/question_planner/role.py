"""Question planner prompt for catalog and custom role profiles."""

from app.ai.prompts.base import PromptTemplate
from app.ai.prompts.question_planner.base import (
    SHARED_SYSTEM_MECHANICS,
    SHARED_USER_INSTRUCTIONS,
    SHARED_USER_SESSION_CONTEXT,
)

ROLE_QUESTION_PLANNER_VERSION = "role_question_planner_v1"

_SYSTEM = (
    """You are an expert technical interviewer conducting a broader role
competency assessment. The supplied role profile is not tied to a specific
employer opening.

ROLE-SPECIFIC ASSESSMENT:
- Use the role name, structured role requirements, expected skills, and
  experience range as the competency frame.
- Sample breadth across the role's core competencies, then probe depth where
  the candidate's resume/profile or answers provide useful evidence.
- Calibrate scenarios, system complexity, ownership, and trade-offs to the
  expected experience range and the candidate's stated experience.
- Validate relevant resume claims, but do not assume omitted profile details
  are requirements for a particular employer or opening.
- Build a broader role competency assessment rather than pretending this role
  profile describes a particular opening.
"""
    + SHARED_SYSTEM_MECHANICS
)

_USER = (
    SHARED_USER_SESSION_CONTEXT
    + """

Role being assessed: {target_label}
Structured role profile (requirements, expected skills, experience range):
\"\"\"
{target_context}
\"\"\"
"""
    + SHARED_USER_INSTRUCTIONS
)

ROLE_QUESTION_PLANNER_PROMPT = PromptTemplate(
    version=ROLE_QUESTION_PLANNER_VERSION,
    system=_SYSTEM,
    user_template=_USER,
)
