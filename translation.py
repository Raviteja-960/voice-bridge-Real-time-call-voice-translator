"""
VoiceBridge AI - Translation REST Routes

POST /api/translate/text          — translate a text string
POST /api/translate/batch         — translate multiple strings
GET  /api/translate/languages     — list supported language pairs
GET  /api/translate/status        — model cache stats
POST /api/translate/detect        — detect language of text
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.dependencies import get_current_user
from app.models.user import UserPublic
from app.services.translation_service import (
    translate,
    translate_batch,
    get_supported_pairs,
    get_cache_stats,
)

router = APIRouter(prefix="/translate", tags=["Translation"])


# ── Request / Response schemas ────────────────────────────────────────────────

class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    source_lang: str = Field(..., min_length=2, max_length=10)
    target_lang: str = Field(..., min_length=2, max_length=10)


class TranslateResponse(BaseModel):
    text: str
    source_lang: str
    target_lang: str
    method: str
    latency_ms: int


class BatchTranslateRequest(BaseModel):
    texts: List[str] = Field(..., max_length=20)
    source_lang: str
    target_lang: str


class DetectRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/text", response_model=TranslateResponse)
async def translate_text(
    data: TranslateRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """Translate a single text string between two languages."""
    try:
        result = await translate(data.text, data.source_lang, data.target_lang)
        return TranslateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Translation failed: {e}")


@router.post("/batch", response_model=List[TranslateResponse])
async def translate_texts(
    data: BatchTranslateRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """Translate up to 20 strings in parallel."""
    try:
        results = await translate_batch(data.texts, data.source_lang, data.target_lang)
        return [TranslateResponse(**r) for r in results]
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("/languages")
async def list_languages():
    """Return all supported direct translation pairs."""
    return {
        "pairs": get_supported_pairs(),
        "total": len(get_supported_pairs()),
        "note": "Unsupported direct pairs are automatically routed via English pivot.",
    }


@router.get("/status")
async def translation_status():
    """Return model cache statistics."""
    return get_cache_stats()


@router.post("/detect")
async def detect_language(
    data: DetectRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Detect the language of a text string using langdetect.
    Falls back to 'en' if detection fails.
    """
    try:
        from langdetect import detect, detect_langs
        lang = detect(data.text)
        probs = detect_langs(data.text)
        return {
            "detected_language": lang,
            "probabilities": [
                {"lang": p.lang, "prob": round(p.prob, 4)} for p in probs[:5]
            ],
        }
    except Exception:
        return {"detected_language": "en", "probabilities": []}
