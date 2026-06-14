# VoiceBridge AI 🎙️🌐

> Real-time AI-powered voice call translation — speak any language, be understood everywhere.

## Architecture

```
Browser ──► Nginx (80) ──► Frontend (React/Vite)
                      └──► Backend  (FastAPI + Socket.IO)
                                └──► MongoDB
                                └──► Whisper STT
                                └──► MarianMT Translation
                                └──► Coqui TTS
```

## Quick Start (Docker)

```bash
# 1. Clone and enter project
cd voicebridge-ai

# 2. Copy env file
cp backend/.env.example backend/.env

# 3. Build and start all services
docker compose up --build

# 4. Open browser
open http://localhost
```

## Production Deployment

```bash
# Generate a local TLS certificate for nginx (optional)
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout nginx/ssl/server.key \
  -out nginx/ssl/server.crt \
  -subj "/CN=localhost"

# Use the production compose override
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# Access the app over HTTPS
open https://localhost
```

## Development (without Docker)

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:socket_app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

### MongoDB
```bash
# Using Docker for just MongoDB
docker run -d -p 27017:27017 --name voicebridge-mongo mongo:7.0
```

## Module Progress

| Module | Feature                        | Status      |
|--------|--------------------------------|-------------|
| 1      | Architecture & Setup           | ✅ Complete |
| 2      | Authentication                 | ✅ Complete |
| 3      | Modern UI/UX                   | ✅ Complete |
| 4      | WebRTC Voice Calling           | ✅ Complete |
| 5      | Whisper Speech-to-Text         | ✅ Complete |
| 6      | MarianMT Translation           | ✅ Complete |
| 7      | Coqui TTS                      | ✅ Complete |
| 8      | Real-time Subtitles            | ✅ Complete |
| 9      | Security & HTTPS               | ✅ Complete |
| 10     | Call History & Transcripts     | ✅ Complete |
| 11     | Production Deployment          | ✅ Complete |
| 12     | PWA / APK Conversion           | ✅ Complete |

## API Docs

Once running: http://localhost/api/docs

## Health Checks

- Backend: http://localhost/api/health
- DB:      http://localhost/api/health/db
