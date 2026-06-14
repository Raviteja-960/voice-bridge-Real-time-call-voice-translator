"""
VoiceBridge AI - Health Check Routes
Used by Docker, Nginx, and monitoring tools to verify service status.
"""
import time
from fastapi import APIRouter
from app.db.mongodb import get_db

router = APIRouter(prefix="/health", tags=["Health"])

_start_time = time.time()


@router.get("/")
async def health_check():
    """Basic liveness probe."""
    return {
        "status": "healthy",
        "service": "VoiceBridge AI Backend",
        "uptime_seconds": round(time.time() - _start_time, 2),
    }


@router.get("/db")
async def db_health():
    """Readiness probe — verifies MongoDB connectivity."""
    try:
        db = get_db()
        await db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        return {"status": "unhealthy", "database": "disconnected", "error": str(exc)}
