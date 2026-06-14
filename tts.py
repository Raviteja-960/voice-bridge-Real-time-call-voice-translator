"""
VoiceBridge AI - TTS REST Routes

POST /api/tts/synthesise   — synthesise text → base64 audio
GET  /api/tts/stream       — stream WAV audio directly (for <audio> src)
GET  /api/tts/status       — model cache status
GET  /api/tts/voices       — list available voices/languages
"""
import base64
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import UserPublic
from app.services.tts_service import synthesise, synthesise_to_wav, get_tts_status, _COQUI_MODELS, _GTTS_FALLBACK_LANGS

router = APIRouter(prefix="/tts", tags=["Text-to-Speech"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SynthesiseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    language: str = Field(default="en", min_length=2, max_length=10)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class SynthesiseResponse(BaseModel):
    audio_base64: str
    language: str
    format: str   # "wav" or "mp3"
    text_length: int


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/synthesise", response_model=SynthesiseResponse)
async def synthesise_text(
    data: SynthesiseRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Synthesise speech from text.
    Returns base64-encoded audio (WAV for Coqui, MP3 for gTTS fallback).
    """
    audio_b64 = await synthesise(data.text, data.language, data.speed)
    if not audio_b64:
        raise HTTPException(status_code=500, detail="TTS synthesis failed.")

    # Detect format from first bytes
    raw = base64.b64decode(audio_b64[:20])
    fmt = "wav" if raw[:4] == b"RIFF" else "mp3"

    return SynthesiseResponse(
        audio_base64=audio_b64,
        language=data.language,
        format=fmt,
        text_length=len(data.text),
    )


@router.get("/stream")
async def stream_audio(
    text: str = Query(..., min_length=1, max_length=500),
    language: str = Query(default="en"),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Stream synthesised audio directly as a WAV/MP3 response.
    Useful for <audio src="/api/tts/stream?text=Hello&language=en"> tags.
    """
    audio_bytes = await synthesise_to_wav(text, language)
    if not audio_bytes:
        raise HTTPException(status_code=500, detail="TTS synthesis failed.")

    # Detect MIME type
    mime = "audio/wav" if audio_bytes[:4] == b"RIFF" else "audio/mpeg"

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type=mime,
        headers={
            "Content-Disposition": f'inline; filename="tts_{language}.{"wav" if mime == "audio/wav" else "mp3"}"',
            "Cache-Control": "no-cache",
        },
    )


@router.get("/status")
async def tts_status():
    """Return TTS model cache status and supported languages."""
    return get_tts_status()


@router.get("/voices")
async def list_voices():
    """List all available TTS voices grouped by engine."""
    coqui_voices = [
        {"language": lang, "engine": "coqui", "model": model}
        for lang, model in _COQUI_MODELS.items()
        if lang != "multilingual"
    ]
    gtts_voices = [
        {"language": lang, "engine": "gtts", "model": "google-tts"}
        for lang in _GTTS_FALLBACK_LANGS
    ]
    return {
        "voices": coqui_voices + gtts_voices,
        "total": len(coqui_voices) + len(gtts_voices),
    }
