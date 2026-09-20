# Guía de instalación — xSlou Clips AI (Fase 1)

## Requisitos
Python 3.11+, Node.js 18+, FFmpeg/FFprobe en el PATH.

## Windows
```powershell
winget install Gyan.FFmpeg
ffmpeg -version
```
Instala Python desde python.org (marca "Add to PATH") y Node.js LTS desde
nodejs.org.

## macOS / Linux
```bash
brew install ffmpeg        # macOS
sudo apt-get install ffmpeg  # Debian/Ubuntu
```

## Backend
```bash
cd apps/backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../../.env.example ../../.env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```
Docs interactivas en `http://localhost:8000/docs`. El primer video que
transcribas descargará el modelo de faster-whisper (puede tardar).

## Frontend
```bash
cd apps/frontend
npm install
npm run dev
```
`http://localhost:3000`, proxea `/api` y `/ws` hacia el backend.

## Variables de entorno (`.env.example`)
`DATABASE_URL`, `STORAGE_ROOT`, `FRONTEND_ORIGIN`, `BACKEND_PORT`,
`WHISPER_MODEL` (default `small`), `WHISPER_DEVICE`, `AI_PROVIDER`
(`rule_based` por defecto, sin claves necesarias), `MAX_UPLOAD_SIZE_MB`,
`ALLOWED_IMPORT_ROOTS`.

## Comandos útiles
```bash
cd apps/backend && pytest
cd apps/backend && alembic revision --autogenerate -m "descripcion"
cd apps/frontend && npm run typecheck
cd apps/frontend && npm run build
python3 scripts/check_setup.py   # verifica ffmpeg/python/node
```

## Problemas comunes
- **ffmpeg no encontrado**: revisa el PATH, reinicia la terminal.
- **Transcripción lenta**: usa `WHISPER_MODEL=tiny` o `base`.
- **Puerto ocupado**: cambia `BACKEND_PORT` en `.env`.
