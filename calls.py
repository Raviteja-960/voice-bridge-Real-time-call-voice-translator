"""
VoiceBridge AI - Call REST Routes
POST   /api/calls/           — create call room
GET    /api/calls/           — list user's calls
GET    /api/calls/{room_id}  — get call details
POST   /api/calls/{room_id}/end — end a call
"""
from typing import List
from fastapi import APIRouter, Depends
from app.models.call import CreateCallRequest, CallResponse
from app.models.base import APIResponse
from app.core.dependencies import get_current_user
from app.models.user import UserPublic
import app.services.call_service as call_svc

router = APIRouter(prefix="/calls", tags=["Calls"])


@router.post("/", response_model=CallResponse, status_code=201)
async def create_call(
    data: CreateCallRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """Create a new call room. Returns room_id for WebRTC signaling."""
    return await call_svc.create_call(current_user.id, data)


@router.get("/", response_model=List[CallResponse])
async def list_calls(current_user: UserPublic = Depends(get_current_user)):
    """Return the authenticated user's recent calls."""
    return await call_svc.get_user_calls(current_user.id)


@router.get("/{room_id}", response_model=CallResponse)
async def get_call(
    room_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    return await call_svc.get_call(room_id)


@router.post("/{room_id}/start", response_model=CallResponse)
async def start_call(
    room_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Mark the call as active once the WebRTC session begins."""
    return await call_svc.start_call(room_id, current_user.id)


@router.post("/{room_id}/end", response_model=CallResponse)
async def end_call(
    room_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    return await call_svc.end_call(room_id, current_user.id)
