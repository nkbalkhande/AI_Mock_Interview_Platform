"""Speech-to-Text service using Groq Whisper.

Groq hosts ``whisper-large-v3-turbo`` as a cloud API — audio is sent to
Groq's servers for transcription.  The SDK call is synchronous so we wrap
it in ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
import io
import logging

from groq import Groq

from app.core.config import settings
from app.core.logging import get_logger

logging.getLogger("groq").setLevel(logging.WARNING)

logger = get_logger(__name__)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


def _transcribe_sync(audio_bytes: bytes, filename: str) -> str:
    """Send audio to Groq Whisper and return the transcript (blocking)."""
    client = _get_client()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = filename

    transcription = client.audio.transcriptions.create(
        file=(filename, audio_file),
        model=settings.STT_MODEL,
        response_format="text",
    )
    return str(transcription).strip()


async def transcribe(audio_bytes: bytes, filename: str) -> str:
    """Async wrapper — offloads the blocking Groq SDK call to a thread."""
    return await asyncio.to_thread(_transcribe_sync, audio_bytes, filename)
