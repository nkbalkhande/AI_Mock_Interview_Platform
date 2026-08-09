"""Backfill: embed every *current* resume version into Qdrant.

Use this after deploying the ingestion pipeline (so resumes uploaded before
it existed get embedded too) or to re-embed after a model/collection change.

Usage (from ``backend/``):

    python -m scripts.backfill_resume_embeddings [--all-versions] [--force]

By default only the current version of each resume is processed, and any
version whose ``extracted_text`` is already set (and thus presumed already
embedded) is skipped. Use ``--force`` to re-run everything regardless, or
``--all-versions`` to also (re-)embed non-current historical versions.
"""

from __future__ import annotations

import argparse
import asyncio

import uuid

from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.logging import configure_logging, get_logger
from app.models.resume import Resume
from app.models.resume_version import ResumeVersion
from app.services.resumes.resume_ingestion_service import ingest_resume_version
from app.services.resumes.resume_vector_store import ResumeVectorStore

logger = get_logger(__name__)


async def _collect_targets(
    *, all_versions: bool, force: bool
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    async with async_session_factory() as session:
        stmt = select(ResumeVersion.id, Resume.user_id).join(
            Resume, ResumeVersion.resume_id == Resume.id
        )
        if not all_versions:
            stmt = stmt.where(ResumeVersion.is_current.is_(True))
        if not force:
            stmt = stmt.where(ResumeVersion.extracted_text.is_(None))

        rows = (await session.execute(stmt)).all()
        return [(row.id, row.user_id) for row in rows]


async def main(*, all_versions: bool, force: bool) -> None:
    configure_logging()
    ResumeVectorStore().ensure_collection()

    targets = await _collect_targets(all_versions=all_versions, force=force)
    logger.info("Backfilling %d resume version(s)", len(targets))

    for resume_version_id, user_id in targets:
        logger.info("Ingesting resume_version_id=%s user_id=%s", resume_version_id, user_id)
        await ingest_resume_version(resume_version_id=resume_version_id, user_id=user_id)

    logger.info("Backfill complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--all-versions",
        action="store_true",
        help="Process every resume version, not just each resume's current one.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-process versions even if extracted_text is already set.",
    )
    args = parser.parse_args()
    asyncio.run(main(all_versions=args.all_versions, force=args.force))
