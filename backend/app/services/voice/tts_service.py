"""Text-to-Speech service using Kokoro.

Kokoro is a local neural TTS model — inference runs on the server CPU/GPU.
The ``KPipeline`` is initialized lazily (first call) so the model download
and load don't block application startup.
"""

from __future__ import annotations

import asyncio
import io
import threading

import numpy as np
import soundfile as sf

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_pipeline = None
_pipeline_lock = threading.Lock()


def _get_pipeline():
    """Lazy singleton for the Kokoro pipeline."""
    global _pipeline
    if _pipeline is None:
        with _pipeline_lock:
            if _pipeline is None:
                from kokoro import KPipeline

                logger.info("Loading Kokoro TTS pipeline (first call)…")
                _pipeline = KPipeline(lang_code="a")
                logger.info("Kokoro TTS pipeline ready.")
    return _pipeline


def _synthesize_sync(text: str) -> bytes:
    """Generate WAV audio from text (blocking — run via ``to_thread``)."""
    pipeline = _get_pipeline()

    samples_list: list[np.ndarray] = []
    for _graphemes, _phonemes, audio in pipeline(
        text,
        voice=settings.voice.tts_voice,
        speed=settings.voice.tts_speed,
    ):
        if audio is not None:
            samples_list.append(audio)

    if not samples_list:
        raise RuntimeError("Kokoro produced no audio output.")

    combined = np.concatenate(samples_list)
    buf = io.BytesIO()
    sf.write(buf, combined, samplerate=24000, format="WAV")
    return buf.getvalue()


async def synthesize(text: str) -> bytes:
    """Async wrapper — offloads CPU-bound Kokoro inference to a thread."""
    return await asyncio.to_thread(_synthesize_sync, text)
