"""Prompt-template primitive."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptTemplate:
    """Immutable prompt with a stable version string.

    ``system`` is rendered once (constant string). ``user_template`` is a
    ``str.format``-style template whose named placeholders are filled at call
    time. Missing placeholders raise ``KeyError`` — deliberate; a
    silently-blank field would produce a subtly-wrong prompt.

    ``version`` is what services persist onto ``interview_evaluations`` /
    session metadata so re-running the exact same prompt later is possible.
    """

    version: str
    system: str
    user_template: str

    def render(self, **variables: object) -> tuple[str, str]:
        return self.system, self.user_template.format(**variables)
