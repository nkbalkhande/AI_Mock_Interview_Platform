"""Domain enumerations.

These mirror the CHECK-constraint value sets defined in the PostgreSQL schema
so the application and database agree on allowed values.
"""

from __future__ import annotations

from enum import StrEnum


class RoleName(StrEnum):
    CANDIDATE = "CANDIDATE"
    INTERVIEWER = "INTERVIEWER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


class InterviewType(StrEnum):
    PRACTICE = "PRACTICE"
    ASSIGNED = "ASSIGNED"


class PracticeType(StrEnum):
    JD_BASED = "JD_BASED"
    ROLE_BASED = "ROLE_BASED"


class InterviewStatus(StrEnum):
    DRAFT = "DRAFT"
    ASSIGNED = "ASSIGNED"
    SCHEDULED = "SCHEDULED"
    AVAILABLE = "AVAILABLE"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AI_EVALUATED = "AI_EVALUATED"
    ADMIN_REVIEW = "ADMIN_REVIEW"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class SessionStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"


class QuestionType(StrEnum):
    TECHNICAL = "TECHNICAL"
    PROJECT = "PROJECT"
    BEHAVIORAL = "BEHAVIORAL"
    CODING = "CODING"
    SYSTEM_DESIGN = "SYSTEM_DESIGN"


class QuestionDifficulty(StrEnum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuestionSource(StrEnum):
    AI_GENERATED = "AI_GENERATED"
    INTERVIEWER_CREATED = "INTERVIEWER_CREATED"


class EvaluationType(StrEnum):
    QUESTION = "QUESTION"
    FINAL = "FINAL"


class AIVerdict(StrEnum):
    CLEARED = "CLEARED"
    NOT_CLEARED = "NOT_CLEARED"
    BORDERLINE = "BORDERLINE"


class AdminDecision(StrEnum):
    CLEARED = "CLEARED"
    NOT_CLEARED = "NOT_CLEARED"
    NEEDS_FURTHER_REVIEW = "NEEDS_FURTHER_REVIEW"


class CodingExecutionStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"
