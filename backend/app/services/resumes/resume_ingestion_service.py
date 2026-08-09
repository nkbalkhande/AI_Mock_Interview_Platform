"""Resume ingestion pipeline: parse -> persist text -> chunk -> embed -> Qdrant.

Runs as a FastAPI ``BackgroundTask`` after the request that created the
resume version has already committed and returned to the client, so it
opens its **own** DB session (the request's session is closed by then).
Every step is defensive: a failure here must never surface to the user or
crash the process — worst case, a resume simply isn't searchable yet and
can be picked up later by the backfill script.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import select

from app.core.constants import RESUME_INGESTION_TIMEOUT_SECONDS
from app.core.database import async_session_factory
from app.core.logging import get_logger
from app.models.resume_version import ResumeVersion
from app.services.resumes.resume_chunker import chunk_text
from app.services.resumes.resume_text_extractor import extract_text
from app.services.resumes.resume_vector_store import ResumeVectorStore
from app.services.storage.file_storage import FileStorageService

logger = get_logger(__name__)


async def ingest_resume_version(
    *,
    resume_version_id: uuid.UUID,
    user_id: uuid.UUID,
) -> None:
    """Entry point for the background task (and the backfill script)."""
    try:
        await asyncio.wait_for(
            _ingest(resume_version_id=resume_version_id, user_id=user_id),
            timeout=RESUME_INGESTION_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        logger.error(
            "Resume ingestion timed out after %ss for resume_version_id=%s",
            RESUME_INGESTION_TIMEOUT_SECONDS,
            resume_version_id,
        )
    except Exception:  # noqa: BLE001 - background task must never raise
        logger.exception(
            "Resume ingestion failed for resume_version_id=%s", resume_version_id
        )


async def _ingest(*, resume_version_id: uuid.UUID, user_id: uuid.UUID) -> None:
    async with async_session_factory() as session:
        version = await session.scalar(
            select(ResumeVersion).where(ResumeVersion.id == resume_version_id)
        )
        if version is None:
            logger.warning("ResumeVersion %s no longer exists; skipping ingestion", resume_version_id)
            return

        file_path = FileStorageService().resolve(version.file_path)
        content_type = version.file_type
        resume_id = version.resume_id
        version_number = version.version_number

        # Extraction is CPU-bound (Docling); keep it off the event loop.
        text = await asyncio.to_thread(extract_text, file_path, content_type)

        version.extracted_text = text or None
        await session.commit()

    if not text:
        logger.warning(
            "No text extracted for resume_version_id=%s; skipping embedding", resume_version_id
        )
        return

    chunks = chunk_text(text)
    if not chunks:
        logger.warning(
            "Extracted text produced no chunks for resume_version_id=%s", resume_version_id
        )
        return

    vectors = await asyncio.to_thread(_embed_chunks, chunks)

    store = ResumeVectorStore()
    await asyncio.to_thread(store.ensure_collection)
    await asyncio.to_thread(
        store.upsert_chunks,
        user_id=user_id,
        resume_id=resume_id,
        resume_version_id=resume_version_id,
        version_number=version_number,
        chunks=chunks,
        vectors=vectors,
    )
    logger.info(
        "Embedded %d chunk(s) for resume_version_id=%s into Qdrant",
        len(chunks),
        resume_version_id,
    )


def _embed_chunks(chunks: list[str]) -> list[list[float]]:
    # Local import keeps the OpenAI client construction (which reads
    # settings) out of this module's import-time side effects.
    from app.ai.llm.embeddings import EmbeddingClient

    return EmbeddingClient().embed_texts(chunks)
