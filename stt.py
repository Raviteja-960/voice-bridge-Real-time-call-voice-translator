"""
VoiceBridge AI - STT REST Routes
POST /api/stt/transcribe  — transcribe a single audio file upload
POST /api/stt/detect      — detect language from audio
GET  /api/stt/status      — model load status
"""
import numpy as np
import soundfile as sf
import io
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from pydantic import BaseModel
from app.core.dependencies import get_current_user
from app.models.user import UserPublic
from app.services.stt_service import transcribe, get_whisper_model

router = APIRouter(prefix="/stt", tags=["Speech-to-Text"])

SUPPORTED_FORMATS = {"wav", "mp3", "ogg", "flac", "webm", "m4a"}
MAX_FILE_MB = 25


class TranscribeResponse(BaseModel):
    text: str
    language: str
    confidence: float
    duration: float
    latency_ms: int


@router.get("/status")
async def model_status():
    """Check if the Whisper model is loaded and ready."""
    from app.services.stt_service import _whisper_model
    return {
        "model_loaded": _whisper_model is not None,
        "status": "ready" if _whisper_model is not None else "loading",
    }


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file (wav/mp3/ogg/flac/webm)"),
    language: str = Form(default=None, description="ISO 639-1 language code or 'auto'"),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Transcribe an uploaded audio file.
    Accepts wav, mp3, ogg, flac, webm, m4a up to 25 MB.
    """
    # Validate file size
    content = await file.read()
    if len(content) > MAX_FILE_MB * 1024 * 1024:
        raise HTTPException(413, f"File too large. Max {MAX_FILE_MB} MB.")

    # Validate format
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in SUPPORTED_FORMATS:
        raise HTTPException(415, f"Unsupported format '{ext}'. Use: {SUPPORTED_FORMATS}")

    # Decode audio to float32 16kHz mono
    try:
        audio_data, sample_rate = sf.read(io.BytesIO(content), dtype="float32", always_2d=False)
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            import librosa
            audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=16000)
        # Mix down to mono
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
    except Exception as e:
        raise HTTPException(422, f"Could not decode audio: {e}")

    lang = None if language in (None, "auto", "") else language
    result = await transcribe(audio_data, language=lang)

    return TranscribeResponse(
        text=result["text"],
        language=result["language"],
        confidence=result["confidence"],
        duration=result["duration"],
        latency_ms=result["latency_ms"],
    )


@router.post("/detect")
async def detect_language(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user),
):
    """Detect the spoken language from the first 30 seconds of audio."""
    import whisper as _whisper

    content = await file.read()
    try:
        audio_data, sr = sf.read(io.BytesIO(content), dtype="float32", always_2d=False)
        if sr != 16000:
            import librosa
            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=16000)
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
    except Exception as e:
        raise HTTPException(422, f"Could not decode audio: {e}")

    model = await get_whisper_model()

    # Use Whisper's built-in language detection on the first 30s
    loop = __import__("asyncio").get_event_loop()
    audio_30s = audio_data[: 16000 * 30]
    mel = await loop.run_in_executor(
        None, lambda: _whisper.log_mel_spectrogram(audio_30s).unsqueeze(0)
    )
    _, probs = await loop.run_in_executor(
        None, lambda: model.detect_language(mel)
    )
    top_lang = max(probs, key=probs.get)

    return {
        "detected_language": top_lang,
        "probabilities": {k: round(v, 4) for k, v in sorted(probs.items(), key=lambda x: -x[1])[:5]},
    }
