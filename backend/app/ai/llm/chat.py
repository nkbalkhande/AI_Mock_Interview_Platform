"""OpenAI chat-completion adapter.

Sibling to ``embeddings.py`` — one thin wrapper per LLM capability so switching
providers or upgrading the SDK only touches this file, and business code
depends on ``ChatLLM`` rather than the raw ``openai`` SDK.

Only synchronous chat completion is exposed (via ``asyncio.to_thread``) for
now — streaming can be added when a UI wants it. JSON-mode is a first-class
option because the interview services always want structured output.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Literal

from openai import OpenAI

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import get_logger

logger = get_logger(__name__)


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
    """Minimal async-friendly chat wrapper over the OpenAI SDK.

    The SDK client is synchronous; we run it in a worker thread so the async
    request handler isn't blocked. Callers should treat the returned string /
    dict as opaque and validate any structured shape themselves.
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
        resolved_key = api_key or settings.OPENAI_API_KEY
        if not resolved_key:
            # Fail loud + early so a misconfigured deploy doesn't silently
            # produce empty interviews. Raised at construction time, not on
            # each request, so the router surfaces a clear 502 immediately.
            raise LLMError(
                "OPENAI_API_KEY is not configured; chat LLM is unavailable."
            )
        self._client = OpenAI(
            api_key=resolved_key,
            timeout=timeout or settings.LLM_REQUEST_TIMEOUT_SECONDS,
        )
        self._model = model or settings.OPENAI_MODEL
        self._temperature = (
            temperature if temperature is not None else settings.LLM_TEMPERATURE
        )
        self._max_tokens = max_tokens or settings.LLM_MAX_OUTPUT_TOKENS

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        json_mode: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Return the assistant's text reply for ``messages``.

        ``json_mode=True`` forces JSON output via the OpenAI ``response_format``
        parameter — required by callers who parse the result. The caller is
        still responsible for parsing/validating; this method just guarantees
        the model is *asked* to return JSON.
        """
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [m.to_dict() for m in messages],
            "temperature": (
                temperature if temperature is not None else self._temperature
            ),
            "max_tokens": max_tokens or self._max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            completion = await asyncio.to_thread(
                lambda: self._client.chat.completions.create(**payload)
            )
        except Exception as exc:  # noqa: BLE001 - normalized into LLMError
            logger.exception("LLM chat completion failed")
            raise LLMError("The language model call failed.") from exc

        try:
            content = completion.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            logger.error("Unexpected LLM completion shape: %r", completion)
            raise LLMError("The language model returned an unexpected shape.") from exc

        if not content.strip():
            raise LLMError("The language model returned an empty response.")
        return content

    async def complete_json(
        self,
        messages: list[ChatMessage],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Convenience: request JSON output and parse it before returning.

        Raises ``LLMError`` if the model returns non-JSON or a non-object
        payload — the JSON-mode contract guarantees valid JSON, but does not
        guarantee an object at the top level, so we check.
        """
        raw = await self.complete(
            messages,
            json_mode=True,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            logger.error("LLM returned non-JSON despite json_mode: %r", raw[:500])
            raise LLMError("The language model returned malformed JSON.") from exc
        if not isinstance(parsed, dict):
            raise LLMError("The language model returned JSON of the wrong shape.")
        return parsed
