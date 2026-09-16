from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config
from .routers import analyze, clips, export, jobs, media, projects, system, upload

app = FastAPI(title="xSlou Clips AI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)
app.include_router(upload.router)
app.include_router(projects.router)
app.include_router(analyze.router)
app.include_router(clips.router)
app.include_router(export.router)
app.include_router(jobs.router)
app.include_router(media.router)


@app.get("/api/health")
def health():
    return {"ok": True}


# El mount de "/" debe ir al final: es un comodín que capturaría cualquier ruta /api/*
# o /media/* registrada después de él.
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
