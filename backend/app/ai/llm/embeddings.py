"""LiteLLM embedding client.

The embedding model is ``settings.embedding.model`` in ``settings/llm.yaml``.
Dimensions must match ``vectordb.qdrant.dense_dim`` in ``settings/config.yaml``.
"""

from __future__ import annotations

from litellm import embedding as litellm_embedding

from app.ai.llm.provider import litellm_kwargs, normalize_model_id
from app.core.config import settings


class EmbeddingClient:
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._model = normalize_model_id(model or settings.embedding.model)
        extra = {"api_key": api_key} if api_key else None
        self._provider_kwargs = litellm_kwargs(self._model, extra=extra)
        self._timeout = settings.embedding.timeout

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, preserving input order."""
        if not texts:
            return []
        response = litellm_embedding(
            model=self._model,
            input=texts,
            timeout=self._timeout,
            **self._provider_kwargs,
        )
        return [
            item["embedding"] if isinstance(item, dict) else list(item.embedding)
            for item in response.data
        ]
