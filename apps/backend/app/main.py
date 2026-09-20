from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import clips, exports, jobs, projects, settings as settings_api, templates, transcripts, videos
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import setup_logging
from app.services.ffmpeg_service import check_ffmpeg_available
from app.websocket import routes as ws_routes
from app.workers import job_queue

setup_logging()
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(title="xSlou Clips AI - Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


app.include_router(projects.router)
app.include_router(videos.router)
app.include_router(jobs.router)
app.include_router(clips.router)
app.include_router(exports.router)
app.include_router(templates.router)
app.include_router(settings_api.router)
app.include_router(transcripts.router)
app.include_router(ws_routes.router)


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "ffmpeg_available": check_ffmpeg_available(),
        "storage_root": str(settings.storage_path),
    }


@app.on_event("startup")
async def on_startup() -> None:
    if not check_ffmpeg_available():
        logger.warning("FFmpeg/FFprobe no se encontraron en el PATH. Instala ffmpeg (ver docs/SETUP.md).")
    import app.models  # noqa: F401  registra todos los modelos en Base.metadata
    from app.database.base import Base
    from app.database.session import engine

    Base.metadata.create_all(bind=engine)  # red de seguridad si no se corrio alembic

    loop = asyncio.get_running_loop()
    job_queue.start_workers(loop, count=settings.max_parallel_jobs)
    await job_queue.recover_pending_jobs()
    logger.info("xSlou Clips AI backend listo en puerto %s", settings.backend_port)
