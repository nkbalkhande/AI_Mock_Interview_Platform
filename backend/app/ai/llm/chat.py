"""LiteLLM chat-completion adapter.

Business code depends on ``ChatLLM``, not a vendor SDK. The active model is
``settings.llm.model`` in ``settings/llm.yaml`` (``openai/…``, ``azure/…``,
``anthropic/…``, ``gemini/…``). Credentials are resolved from config / .env.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal

import litellm
from litellm import acompletion

from app.ai.llm.provider import (
    litellm_kwargs,
    normalize_model_id,
    temperature_kwargs,
    token_limit_kwargs,
)
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)

litellm.drop_params = True
litellm.suppress_debug_info = True

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


class LLMError(AppException):
    """Raised when the underlying LLM call fails or returns unusable content."""

    status_code = 502
    error_code = "llm_error"
    message = "Failed to generate a response from the language model."


ChatRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True)
class ChatMessage:
    role: ChatRole
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}


class ChatLLM:
    """Async chat wrapper over LiteLLM.

    Callers should treat the returned string / dict as opaque and validate
    any structured shape themselves.
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._model = normalize_model_id(model or settings.llm.model)
        self._temperature = (
            temperature if temperature is not None else settings.llm.temperature
        )
        self._max_tokens = max_tokens or settings.llm.max_completion_tokens
        self._timeout = timeout or settings.llm.timeout
        extra = dict(settings.llm.kwargs)
        if api_key:
            extra["api_key"] = api_key
        try:
            self._provider_kwargs = litellm_kwargs(self._model, extra=extra)
        except ValueError as exc:
            raise LLMError(str(exc)) from exc

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Return the assistant's text reply for ``messages``."""
        limit = max_tokens or self._max_tokens
        chosen_temperature = (
            temperature if temperature is not None else self._temperature
        )
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "timeout": self._timeout,
            **temperature_kwargs(self._model, chosen_temperature),
            **token_limit_kwargs(self._model, limit),
            **self._provider_kwargs,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            completion = await acompletion(**payload)
        except Exception as exc:  # noqa: BLE001 - normalized into LLMError
            logger.exception("LLM chat completion failed")
            raise LLMError("The language model call failed.") from exc

        try:
            content = completion.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            logger.error("Unexpected LLM completion shape: %r", completion)
            raise LLMError("The language model returned an unexpected shape.") from exc

        if not str(content).strip():
            raise LLMError("The language model returned an empty response.")
        return str(content)

    async def complete_json(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Request JSON output and parse it before returning."""
        raw = await self.complete(
            messages,
            json_mode=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = _FENCE_RE.sub("", raw.strip())
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned non-JSON despite json_mode: %r", raw[:500])
            raise LLMError("The language model returned malformed JSON.") from exc
        if not isinstance(parsed, dict):
            raise LLMError("The language model returned JSON of the wrong shape.")
        return parsed
