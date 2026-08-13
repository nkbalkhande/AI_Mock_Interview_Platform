"""Qdrant adapter for resume chunk embeddings (AD-16).

Design (answers "1000+ users -> 1 collection-per-user is bad"):

- **One shared collection** (``settings.vectordb.collection``) holds
  every chunk from every candidate's resume. Qdrant collections are meant
  to scale to millions of points; a collection per user would multiply
  fixed per-collection overhead (HNSW index, segments, payload indexes) by
  the user count for no benefit.
- **Multi-tenancy is payload-based.** Every point carries ``user_id``,
  ``resume_id``, ``resume_version_id`` and ``chunk_index`` in its payload.
  Retrieval always filters by ``resume_version_id`` (or ``user_id``)
  alongside the vector search. Payload indexes on those two fields keep
  filtered queries fast as the collection grows.
- **Point IDs are deterministic** (``uuid5`` of ``resume_version_id:chunk_index``),
  so re-running ingestion for the same version overwrites the same points
  instead of duplicating them (idempotent upsert).
- **Resume updates never mutate old vectors.** A new resume version gets
  its own ``resume_version_id`` and therefore entirely new points; old
  points are left alone. Postgres (``resumes.current_version_number``) is
  the single source of truth for "which version is current" — callers
  resolve that first, then filter Qdrant by the exact version id, so there
  is no dual-write flag to keep in sync between the two stores.
"""

from __future__ import annotations

import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_POINT_ID_NAMESPACE = uuid.UUID("2b7f6b3a-1b8b-4c9e-9f0a-8d6a7b5c4e3f")


def _point_id(resume_version_id: uuid.UUID, chunk_index: int) -> str:
    return str(uuid.uuid5(_POINT_ID_NAMESPACE, f"{resume_version_id}:{chunk_index}"))


@lru_cache
def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        host=settings.vectordb.qdrant.host,
        port=settings.vectordb.qdrant.port,
        api_key=settings.QDRANT_API_KEY,
        https=settings.vectordb.qdrant.https,
    )


class ResumeVectorStore:
    def __init__(self, client: QdrantClient | None = None) -> None:
        self._client = client or get_qdrant_client()
        self._collection = settings.vectordb.collection

    def ensure_collection(self) -> None:
        """Create the shared collection + payload indexes if missing (idempotent)."""
        if not self._client.collection_exists(self._collection):
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=qmodels.VectorParams(
                    size=settings.embedding.dimensions,
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection %s", self._collection)

        for field_name, schema in (
            ("user_id", qmodels.PayloadSchemaType.KEYWORD),
            ("resume_version_id", qmodels.PayloadSchemaType.KEYWORD),
        ):
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name=field_name,
                field_schema=schema,
            )

    def upsert_chunks(
        self,
        *,
        user_id: uuid.UUID,
        resume_id: uuid.UUID,
        resume_version_id: uuid.UUID,
        version_number: int,
        chunks: list[str],
        vectors: list[list[float]],
    ) -> None:
        """Upsert one point per chunk. Idempotent via deterministic point ids."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must be the same length")
        if not chunks:
            return

        points = [
            qmodels.PointStruct(
                id=_point_id(resume_version_id, index),
                vector=vector,
                payload={
                    "user_id": str(user_id),
                    "resume_id": str(resume_id),
                    "resume_version_id": str(resume_version_id),
                    "version_number": version_number,
                    "chunk_index": index,
                    "text": chunk,
                },
            )
            for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
        ]
        self._client.upsert(collection_name=self._collection, points=points)

    def delete_by_resume_version(self, resume_version_id: uuid.UUID) -> None:
        """Best-effort cleanup, e.g. if ingestion needs to be retried from scratch."""
        self._client.delete(
            collection_name=self._collection,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[
                        qmodels.FieldCondition(
                            key="resume_version_id",
                            match=qmodels.MatchValue(value=str(resume_version_id)),
                        )
                    ]
                )
            ),
        )
