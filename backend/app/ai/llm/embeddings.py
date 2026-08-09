"""OpenAI embedding client (AD-16).

Thin adapter so callers depend on this module, not the ``openai`` SDK
directly — swapping providers later only touches this file.
"""

from __future__ import annotations

from openai import OpenAI

from app.core.config import settings


class EmbeddingClient:
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key or settings.OPENAI_API_KEY)
        self._model = model or settings.EMBEDDING_MODEL

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving input order."""
        if not texts:
            return []
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in response.data]
