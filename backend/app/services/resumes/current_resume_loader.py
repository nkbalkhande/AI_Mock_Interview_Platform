"""Load the current resume for a user so the interview engine can snapshot
its version id + extracted text at interview creation time.

Practice interviews must **freeze** the resume: if the candidate later
uploads a new version, an already-started interview should still be
evaluated against the resume they had at start. We enforce that by:

1. Reading the ``is_current`` ResumeVersion at creation.
2. Storing its id on ``interviews.resume_version_id`` (already a column).
3. Snapshotting the extracted text into the session's ``interview_state``.

If a candidate has no resume yet, ``get_current_for_user`` returns ``None``
so the caller can respond with a clear "please upload a resume" error
rather than start a broken interview.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resume import Resume
from app.models.resume_version import ResumeVersion


@dataclass(frozen=True)
class CurrentResume:
    version_id: uuid.UUID
    extracted_text: str | None
    file_name: str

    @property
    def has_text(self) -> bool:
        return bool(self.extracted_text and self.extracted_text.strip())


class CurrentResumeLoader:
    """Reads the candidate's current ResumeVersion (``is_current=True``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_current_for_user(
        self, user_id: uuid.UUID
    ) -> CurrentResume | None:
        # Filter on the partial-unique constraint on `is_current = true` — at
        # most one row per user matches, so a simple scalar fetch is safe.
        stmt = (
            select(ResumeVersion)
            .join(Resume, ResumeVersion.resume_id == Resume.id)
            .where(
                Resume.user_id == user_id,
                ResumeVersion.is_current.is_(True),
            )
            .limit(1)
        )
        version = (await self._session.execute(stmt)).scalar_one_or_none()
        if version is None:
            return None
        return CurrentResume(
            version_id=version.id,
            extracted_text=version.extracted_text,
            file_name=version.file_name,
        )
