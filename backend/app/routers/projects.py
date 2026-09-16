from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from .. import ffmpeg_utils, storage
from ..models import Project, ProjectConfig

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("")
def create_project(video_id: str, config: ProjectConfig):
    meta_file = storage.upload_dir(video_id) / "meta.json"
    if not meta_file.exists():
        raise HTTPException(404, "Video no encontrado. Súbelo primero.")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))

    project = Project(
        id=storage.new_id(),
        video_id=video_id,
        original_filename=meta["filename"],
        duration=meta["duration"],
        width=meta["width"],
        height=meta["height"],
        fps=meta["fps"],
        config=config,
        clips=[],
        created_at=storage.now_iso(),
    )
    storage.save_project(project)
    return project


@router.get("")
def list_projects():
    return storage.list_projects()


@router.get("/{project_id}")
def get_project(project_id: str):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    return project


@router.put("/{project_id}/config")
def update_config(project_id: str, config: ProjectConfig):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    project.config = config
    storage.save_project(project)
    return project


@router.delete("/{project_id}")
def delete_project(project_id: str):
    storage.delete_project(project_id)
    return {"ok": True}
