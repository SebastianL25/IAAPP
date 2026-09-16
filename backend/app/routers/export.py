from __future__ import annotations

import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .. import config, export as export_engine, ffmpeg_utils, jobs, storage
from ..ffmpeg_utils import FORMAT_RESOLUTIONS
from ..jobs import ProgressReporter

router = APIRouter(prefix="/api/projects", tags=["export"])


def _update_clip(project_id: str, clip_id: str, **fields) -> None:
    project = storage.load_project(project_id)
    if not project:
        return
    for c in project.clips:
        if c.id == clip_id:
            for k, v in fields.items():
                setattr(c, k, v)
            break
    storage.save_project(project)


def _run_export(reporter: ProgressReporter, project_id: str, clip_id: str) -> dict:
    project = storage.load_project(project_id)
    if not project:
        raise RuntimeError("Proyecto no encontrado")
    clip = next((c for c in project.clips if c.id == clip_id), None)
    if not clip:
        raise RuntimeError("Clip no encontrado")

    _update_clip(project_id, clip_id, export_status="processing", export_progress=0.0, export_error=None)
    try:
        source = storage.source_video_path(project.video_id)
        probe = ffmpeg_utils.probe(source)
        out_dir = storage.export_dir(project_id)
        out_path = out_dir / f"{clip_id}.mp4"

        ass_path = None
        if clip.subtitles_enabled and clip.subtitles:
            reporter.stage("Generando subtítulos")
            out_w, out_h = FORMAT_RESOLUTIONS[clip.format]
            ass_path = out_dir / f"{clip_id}.ass"
            export_engine.write_ass_for_clip(clip, out_w, out_h, ass_path)

        reporter.stage("Renderizando video final")
        log_path = config.LOGS_DIR / f"export_{clip_id}.log"
        mute_intervals = [tuple(m) for m in clip.mute_intervals]
        export_engine.export_clip(
            project.config,
            clip,
            probe,
            source,
            ass_path,
            out_path,
            mute_intervals=mute_intervals,
            on_progress=reporter.progress,
            cancel_event=reporter.cancel_event,
            log_path=log_path,
        )
        _update_clip(project_id, clip_id, export_status="done", export_progress=1.0, export_path=str(out_path))
        return {"path": str(out_path)}
    except InterruptedError:
        _update_clip(project_id, clip_id, export_status="cancelled")
        raise
    except Exception as exc:  # noqa: BLE001
        _update_clip(project_id, clip_id, export_status="error", export_error=str(exc))
        raise


@router.post("/{project_id}/clips/{clip_id}/export")
def export_clip_endpoint(project_id: str, clip_id: str):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    if not any(c.id == clip_id for c in project.clips):
        raise HTTPException(404, "Clip no encontrado")
    if not config.resolve_ffmpeg():
        raise HTTPException(400, "ffmpeg no está configurado. Ve a Ajustes y define su ruta.")

    _update_clip(project_id, clip_id, export_status="queued", export_progress=0.0)
    job_id = jobs.submit(
        "export", project_id, lambda reporter: _run_export(reporter, project_id, clip_id), extra={"clip_id": clip_id}
    )
    return {"job_id": job_id}


@router.post("/{project_id}/export-all")
def export_all(project_id: str):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    if not config.resolve_ffmpeg():
        raise HTTPException(400, "ffmpeg no está configurado. Ve a Ajustes y define su ruta.")

    job_ids = []
    for c in project.clips:
        _update_clip(project_id, c.id, export_status="queued", export_progress=0.0)
        job_id = jobs.submit(
            "export", project_id, lambda reporter, cid=c.id: _run_export(reporter, project_id, cid),
            extra={"clip_id": c.id},
        )
        job_ids.append({"clip_id": c.id, "job_id": job_id})
    return {"jobs": job_ids}


@router.get("/{project_id}/clips/{clip_id}/download")
def download_clip(project_id: str, clip_id: str):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    clip = next((c for c in project.clips if c.id == clip_id), None)
    if not clip or not clip.export_path or not Path(clip.export_path).exists():
        raise HTTPException(404, "El clip aún no ha sido exportado")
    return FileResponse(clip.export_path, media_type="video/mp4", filename=f"clip_{clip_id}.mp4")


@router.get("/{project_id}/export/zip")
def download_zip(project_id: str):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    done_clips = [c for c in project.clips if c.export_path and Path(c.export_path).exists()]
    if not done_clips:
        raise HTTPException(400, "No hay clips exportados todavía.")

    zip_path = storage.export_dir(project_id) / "clips.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, c in enumerate(done_clips, start=1):
            zf.write(c.export_path, arcname=f"clip_{i:02d}_{c.id}.mp4")
    return FileResponse(zip_path, media_type="application/zip", filename=f"{project_id}_clips.zip")
