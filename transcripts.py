"""
VoiceBridge AI - Transcript REST Routes

GET  /api/transcripts/                    — list user's transcripts
GET  /api/transcripts/{room_id}           — get full transcript
GET  /api/transcripts/{room_id}/export    — export as SRT/VTT/TXT/JSON
GET  /api/transcripts/{room_id}/summary   — AI-generated call summary
DELETE /api/transcripts/{room_id}         — delete transcript
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import List

from app.core.dependencies import get_current_user
from app.models.user import UserPublic
from app.models.transcript import TranscriptResponse, SubtitleExportFormat
from app.models.base import APIResponse
from app.services.subtitle_service import (
    get_transcript,
    get_user_transcripts,
    export_transcript,
    generate_summary,
)

router = APIRouter(prefix="/transcripts", tags=["Transcripts"])

EXPORT_MIME = {
    SubtitleExportFormat.SRT:  "text/plain",
    SubtitleExportFormat.VTT:  "text/vtt",
    SubtitleExportFormat.TXT:  "text/plain",
    SubtitleExportFormat.JSON: "application/json",
}


@router.get("/", response_model=List[TranscriptResponse])
async def list_transcripts(
    current_user: UserPublic = Depends(get_current_user),
):
    """Return all transcripts for the authenticated user's calls."""
    return await get_user_transcripts(current_user.id)


@router.get("/{room_id}", response_model=TranscriptResponse)
async def get_call_transcript(
    room_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Return the full transcript for a specific call room."""
    transcript = await get_transcript(room_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    return transcript


@router.get("/{room_id}/export")
async def export_call_transcript(
    room_id: str,
    format: SubtitleExportFormat = Query(default=SubtitleExportFormat.SRT),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Export a call transcript in the requested format.
    Supported: srt, vtt, txt, json
    """
    content = await export_transcript(room_id, format)
    if not content:
        raise HTTPException(status_code=404, detail="Transcript not found or empty.")

    ext = format.value
    mime = EXPORT_MIME.get(format, "text/plain")

    return PlainTextResponse(
        content=content,
        media_type=mime,
        headers={
            "Content-Disposition": f'attachment; filename="transcript_{room_id}.{ext}"',
        },
    )


@router.get("/{room_id}/summary")
async def get_call_summary(
    room_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Return an AI-generated summary of the call transcript."""
    summary = await generate_summary(room_id)
    return {"room_id": room_id, "summary": summary}


@router.delete("/{room_id}", response_model=APIResponse)
async def delete_transcript(
    room_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Delete a transcript (irreversible)."""
    from app.db.mongodb import get_db
    db = get_db()
    result = await db.transcripts.delete_one({"room_id": room_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transcript not found.")
    return APIResponse(success=True, message="Transcript deleted.")
