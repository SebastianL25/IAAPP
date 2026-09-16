"""Persistencia simple basada en archivos JSON (proyectos, clips, subida de video)."""
from __future__ import annotations

import json
import shutil
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import config
from .models import Project

_lock = threading.Lock()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def upload_dir(video_id: str) -> Path:
    d = config.UPLOADS_DIR / video_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def project_dir(project_id: str) -> Path:
    d = config.PROJECTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def project_file(project_id: str) -> Path:
    return project_dir(project_id) / "project.json"


def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(path.suffix + f".tmp{uuid.uuid4().hex[:8]}")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def save_project(project: Project) -> None:
    with _lock:
        _atomic_write(project_file(project.id), project.model_dump_json(indent=2))


def load_project(project_id: str) -> Optional[Project]:
    f = project_file(project_id)
    if not f.exists():
        return None
    data = json.loads(f.read_text(encoding="utf-8"))
    return Project.model_validate(data)


def list_projects() -> list[Project]:
    out = []
    for d in sorted(config.PROJECTS_DIR.glob("*")):
        f = d / "project.json"
        if f.exists():
            try:
                out.append(Project.model_validate(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                continue
    out.sort(key=lambda p: p.created_at, reverse=True)
    return out


def delete_project(project_id: str) -> None:
    d = project_dir(project_id)
    if d.exists():
        shutil.rmtree(d)


def analysis_file(project_id: str) -> Path:
    return project_dir(project_id) / "analysis.json"


def save_analysis(project_id: str, data: dict) -> None:
    _atomic_write(analysis_file(project_id), json.dumps(data, ensure_ascii=False, indent=2))


def load_analysis(project_id: str) -> Optional[dict]:
    f = analysis_file(project_id)
    if not f.exists():
        return None
    return json.loads(f.read_text(encoding="utf-8"))


def source_video_path(video_id: str) -> Path:
    meta_file = upload_dir(video_id) / "meta.json"
    if meta_file.exists():
        meta = json.loads(meta_file.read_text(encoding="utf-8"))
        return upload_dir(video_id) / meta["filename"]
    raise FileNotFoundError("No se encontró el video subido")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def export_dir(project_id: str) -> Path:
    d = config.EXPORTS_DIR / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d
