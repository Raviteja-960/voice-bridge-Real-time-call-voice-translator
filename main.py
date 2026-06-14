"""
VoiceBridge AI - Application Entry Point
Mounts FastAPI + Socket.IO under a single ASGI app served by Uvicorn.
"""
import logging
import socketio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from app.db.mongodb import connect_db, close_db
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.calls import router as calls_router
from app.api.routes.stt import router as stt_router
from app.api.routes.translation import router as translation_router
from app.api.routes.tts import router as tts_router
from app.api.routes.transcripts import router as transcripts_router
from app.sockets.manager import sio

# ── Bootstrap logging before anything else ───────────────────────────────────
setup_logging()
logger = logging.getLogger(__name__)


# ── App lifespan (startup / shutdown hooks) ───────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("VoiceBridge AI starting up ...")
    await connect_db()

    # Pre-warm Whisper model in background so first call isn't slow
    async def _warm_whisper():
        try:
            from app.services.stt_service import get_whisper_model
            await get_whisper_model()
        except Exception as e:
            logger.warning("Whisper warm-up failed (non-fatal): %s", e)

    import asyncio
    asyncio.create_task(_warm_whisper())

    yield
    logger.info("VoiceBridge AI shutting down ...")
    await close_db()


# ── FastAPI application ───────────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered real-time voice call translation platform",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(health_router,      prefix="/api")
app.include_router(auth_router,        prefix="/api")
app.include_router(calls_router,       prefix="/api")
app.include_router(stt_router,         prefix="/api")
app.include_router(translation_router, prefix="/api")
app.include_router(tts_router,         prefix="/api")
app.include_router(transcripts_router, prefix="/api")

# ── Root endpoint ─────────────────────────────────────────────────────────────
@app.get("/api")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/api/docs",
    }


# ── Mount Socket.IO alongside FastAPI ────────────────────────────────────────
# All Socket.IO traffic goes to /socket.io/*
# All REST traffic goes to /api/*
socket_app = socketio.ASGIApp(sio, other_asgi_app=app, socketio_path="/socket.io")

# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:socket_app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
