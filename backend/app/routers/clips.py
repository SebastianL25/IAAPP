from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import storage, subtitles
from ..models import ClipConfig

router = APIRouter(prefix="/api/projects", tags=["clips"])


def _find_clip(project, clip_id: str) -> ClipConfig:
    for c in project.clips:
        if c.id == clip_id:
            return c
    raise HTTPException(404, "Clip no encontrado")


@router.put("/{project_id}/clips/{clip_id}")
def update_clip(project_id: str, clip_id: str, clip: ClipConfig):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    clip.id = clip_id
    for i, c in enumerate(project.clips):
        if c.id == clip_id:
            project.clips[i] = clip
            storage.save_project(project)
            return clip
    raise HTTPException(404, "Clip no encontrado")


@router.post("/{project_id}/clips/{clip_id}/apply-to-all")
def apply_crop_to_all(project_id: str, clip_id: str):
    """Copia formato, tipo de stream y encuadre de un clip a todos los demás del proyecto."""
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    source = _find_clip(project, clip_id)
    for c in project.clips:
        if c.id == clip_id:
            continue
        c.format = source.format
        c.stream_type = source.stream_type
        c.camera_rect = source.camera_rect
        c.content_rect = source.content_rect
        c.keep_full_vertical_game = source.keep_full_vertical_game
        c.kick_username = source.kick_username
    storage.save_project(project)
    return project


@router.post("/{project_id}/clips/{clip_id}/recompute-subtitles")
def recompute_subtitles(project_id: str, clip_id: str):
    """Reconstruye los subtítulos de un clip tras mover manualmente su inicio/fin."""
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    clip = _find_clip(project, clip_id)
    analysis_data = storage.load_analysis(project_id)
    if not analysis_data:
        raise HTTPException(400, "No hay una transcripción disponible; ejecuta el análisis primero.")
    from .. import config as app_config

    segments = analysis_data.get("segments", [])
    words = subtitles.words_in_range(segments, clip.start, clip.end)
    blocks = subtitles.build_subtitle_blocks(words, clip.start, clip.end)
    censored_words = app_config.get_settings().get("censored_words", [])
    blocks, mute_intervals = subtitles.apply_censorship(blocks, words, clip.start, censored_words)
    clip.subtitles = blocks
    clip.mute_intervals = [list(m) for m in mute_intervals]
    storage.save_project(project)
    return clip
