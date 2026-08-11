"""Voice API — TTS and STT endpoints for the interview voice engine."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.api.dependencies.auth import get_current_user
from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.user import User
from app.services.voice import stt_service, tts_service

router = APIRouter()

_STT_AUDIO_TYPES = frozenset(
    {
        "audio/webm",
        "audio/ogg",
        "audio/wav",
        "audio/x-wav",
        "audio/mpeg",
        "audio/mp4",
        "audio/flac",
        "audio/x-m4a",
        "video/webm",
    }
)


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class SttResponse(BaseModel):
    transcript: str


@router.post("/tts")
async def text_to_speech(
    payload: TtsRequest,
    _current_user: User = Depends(get_current_user),
) -> Response:
    """Convert text to speech audio (WAV) using Kokoro TTS."""
    if not payload.text.strip():
        raise ValidationError("Text must not be blank.")

    wav_bytes = await tts_service.synthesize(payload.text)
    return Response(content=wav_bytes, media_type="audio/wav")


@router.post("/stt", response_model=SttResponse)
async def speech_to_text(
    audio: UploadFile = File(...),
    _current_user: User = Depends(get_current_user),
) -> SttResponse:
    """Transcribe audio to text using Groq Whisper."""
    if not settings.GROQ_API_KEY:
        raise ValidationError("Speech-to-text is not configured.")

    data = await audio.read()
    if not data:
        raise ValidationError("The audio file is empty.")

    max_bytes = 25 * 1024 * 1024
    if len(data) > max_bytes:
        raise ValidationError("Audio file exceeds the 25MB limit.")

    content_type = (audio.content_type or "").lower().split(";")[0].strip()
    if content_type not in _STT_AUDIO_TYPES:
        raise ValidationError(
            f"Unsupported audio type: {content_type or 'unknown'}."
        )

    transcript = await stt_service.transcribe(
        data, audio.filename or "audio.webm"
    )
    return SttResponse(transcript=transcript)
