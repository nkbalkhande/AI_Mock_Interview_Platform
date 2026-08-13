"""Resolve LiteLLM model ids and provider credentials from config.

``settings/llm.yaml`` holds the model id (``openai/...``, ``azure/...``,
``anthropic/...``, ``gemini/...``). This module maps that prefix onto the
API key / endpoint LiteLLM needs, reading secrets from environment-backed
settings — never from the YAML file.
"""

from __future__ import annotations

from typing import Any

from app.core.config import settings

_PROVIDER_ALIASES = {
    "claude": "anthropic",
    "google": "gemini",
    "google_ai": "gemini",
}

_BARE_PREFIXES = (
    ("claude", "anthropic"),
    ("gemini", "gemini"),
    ("gpt-", "openai"),
    ("o1", "openai"),
    ("o3", "openai"),
    ("o4", "openai"),
    ("text-embedding-", "openai"),
)


def normalize_model_id(model: str) -> str:
    """Return a LiteLLM model id with an explicit provider prefix."""
    value = (model or "").strip()
    if not value:
        raise ValueError("LLM model id is empty.")
    if "/" in value:
        return value
    lower = value.lower()
    for prefix, provider in _BARE_PREFIXES:
        if lower.startswith(prefix):
            return f"{provider}/{value}"
    return f"openai/{value}"


def provider_from_model(model: str) -> str:
    """Return the canonical provider name for a LiteLLM model id."""
    normalized = normalize_model_id(model)
    prefix = normalized.split("/", 1)[0].lower()
    return _PROVIDER_ALIASES.get(prefix, prefix)


def credentials_for(model: str) -> dict[str, Any]:
    """LiteLLM kwargs (api_key, api_base, api_version) for ``model``."""
    provider = provider_from_model(model)
    if provider == "openai":
        return _require_key("openai", settings.OPENAI_API_KEY)
    if provider == "azure":
        azure = settings.llm.providers.azure
        creds = _require_key("azure", settings.AZURE_OPENAI_API_KEY)
        api_base = azure.api_base or settings.AZURE_OPENAI_ENDPOINT
        if not api_base:
            raise ValueError(
                "Azure OpenAI is selected but AZURE_OPENAI_ENDPOINT is not set. "
                "Add it to backend/.env."
            )
        creds["api_base"] = api_base
        creds["api_version"] = azure.api_version
        return creds
    if provider == "anthropic":
        return _require_key("anthropic", settings.ANTHROPIC_API_KEY)
    if provider == "gemini":
        key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        return _require_key("gemini", key)
    raise ValueError(
        f"Unsupported LLM provider {provider!r} in model {model!r}. "
        "Use openai/, azure/, anthropic/, or gemini/."
    )


def is_openai_reasoning_model(model: str) -> bool:
    """GPT-5 and o-series models have a restricted Chat Completions surface."""
    slug = normalize_model_id(model).rsplit("/", 1)[-1].lower()
    return slug.startswith(("gpt-5", "o1", "o3", "o4"))


def uses_max_completion_tokens(model: str) -> bool:
    """GPT-5 and OpenAI reasoning models reject ``max_tokens``."""
    return is_openai_reasoning_model(model)


def token_limit_kwargs(model: str, limit: int) -> dict[str, int]:
    """Return the token-cap kwarg the target model accepts."""
    if uses_max_completion_tokens(model):
        return {"max_completion_tokens": limit}
    return {"max_tokens": limit}


def temperature_kwargs(model: str, temperature: float | None) -> dict[str, float]:
    """Omit temperature when the model only accepts the API default (1)."""
    if temperature is None or is_openai_reasoning_model(model):
        return {}
    return {"temperature": temperature}


def litellm_kwargs(model: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Merge provider credentials with optional per-call extras."""
    payload = credentials_for(model)
    if extra:
        payload.update(extra)
    return payload


def _require_key(provider: str, api_key: str | None) -> dict[str, Any]:
    if not api_key:
        env_name = {
            "openai": "OPENAI_API_KEY",
            "azure": "AZURE_OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
        }.get(provider, f"{provider.upper()}_API_KEY")
        raise ValueError(
            f"{provider} is selected in settings/llm.yaml but {env_name} "
            "is not set. Add it to backend/.env."
        )
    return {"api_key": api_key}
