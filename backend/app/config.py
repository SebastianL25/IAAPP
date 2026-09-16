"""Configuración persistente de la aplicación (ruta de ffmpeg, modelo de Whisper, etc.)."""
from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from typing import Any, Dict

# Carpeta base de datos de la app. Puede sobreescribirse con la variable de
# entorno XSLOU_DATA_DIR (usada por el lanzador de Windows para apuntar a
# %APPDATA%\xSlouClipsAI si se desea).
BASE_DIR = Path(os.environ.get("XSLOU_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))

UPLOADS_DIR = BASE_DIR / "uploads"
PROJECTS_DIR = BASE_DIR / "projects"
JOBS_DIR = BASE_DIR / "jobs"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"
MODELS_DIR = BASE_DIR / "models"
CONFIG_FILE = BASE_DIR / "config.json"

for d in (BASE_DIR, UPLOADS_DIR, PROJECTS_DIR, JOBS_DIR, LOGS_DIR, EXPORTS_DIR, MODELS_DIR):
    d.mkdir(parents=True, exist_ok=True)

DEFAULT_SETTINGS: Dict[str, Any] = {
    "ffmpeg_path": "",  # vacío = buscar "ffmpeg" en PATH
    "ffprobe_path": "",
    "whisper_model": "medium",  # tiny, base, small, medium, large-v3
    "whisper_device": "auto",  # auto, cuda, cpu
    "compute_type": "auto",
    "censored_words": ["puta", "mierda", "pendejo", "carajo", "coño"],
}

_lock = threading.Lock()


def _load() -> Dict[str, Any]:
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
    else:
        data = {}
    merged = {**DEFAULT_SETTINGS, **data}
    return merged


def get_settings() -> Dict[str, Any]:
    with _lock:
        return _load()


def update_settings(patch: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        current = _load()
        current.update({k: v for k, v in patch.items() if v is not None})
        tmp = CONFIG_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(CONFIG_FILE)
        return current


def resolve_ffmpeg() -> str | None:
    settings = get_settings()
    configured = settings.get("ffmpeg_path") or ""
    if configured and Path(configured).exists():
        return configured
    found = shutil.which("ffmpeg")
    return found


def resolve_ffprobe() -> str | None:
    settings = get_settings()
    configured = settings.get("ffprobe_path") or ""
    if configured and Path(configured).exists():
        return configured
    found = shutil.which("ffprobe")
    return found
