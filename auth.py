"""
VoiceBridge AI - Authentication Routes
POST /api/auth/signup
POST /api/auth/login
POST /api/auth/refresh
GET  /api/auth/me
PATCH /api/auth/me
POST /api/auth/change-password
POST /api/auth/logout
"""
from fastapi import APIRouter, Depends, status
from app.models.user import (
    SignupRequest,
    LoginRequest,
    RefreshTokenRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    AuthResponse,
    UserPublic,
)
from app.models.base import APIResponse
from app.core.dependencies import get_current_user
import app.services.auth_service as auth_svc

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(data: SignupRequest):
    """Register a new user and return JWT tokens."""
    return await auth_svc.signup(data)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest):
    """Authenticate with email + password and return JWT tokens."""
    return await auth_svc.login(data)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(data: RefreshTokenRequest):
    """Exchange a valid refresh token for a new token pair."""
    return await auth_svc.refresh_tokens(data.refresh_token)


@router.get("/me", response_model=UserPublic)
async def get_me(current_user: UserPublic = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserPublic)
async def update_me(
    data: UpdateProfileRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """Update display name, preferred language, or avatar."""
    return await auth_svc.update_profile(current_user.id, data)


@router.post("/change-password", response_model=APIResponse)
async def change_password(
    data: ChangePasswordRequest,
    current_user: UserPublic = Depends(get_current_user),
):
    """Change the authenticated user's password."""
    result = await auth_svc.change_password(current_user.id, data)
    return APIResponse(success=True, message=result["message"])


@router.post("/logout", response_model=APIResponse)
async def logout(current_user: UserPublic = Depends(get_current_user)):
    """
    Client-side logout — instructs the client to discard tokens.
    (Server-side token blacklisting added in Module 9.)
    """
    return APIResponse(success=True, message="Logged out successfully.")
