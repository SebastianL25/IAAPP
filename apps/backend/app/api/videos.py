from __future__ import annotations

import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import InvalidFileError, NotFoundError
from app.database.session import get_db
from app.models.clip import ClipCandidate
from app.models.job import ProcessingJob
from app.models.video import DetectedEvent, SourceVideo, Transcript
from app.schemas.video import (
    ImportFolderRequest,
    ImportPathRequest,
    SourceVideoOut,
    VideoAnalysisOut,
)
from app.services import import_service
from app.workers import job_queue

router = APIRouter(prefix="/api/videos", tags=["videos"])

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")
CHUNK_SIZE = 1024 * 1024


def _to_out(video: SourceVideo) -> SourceVideoOut:
    data = SourceVideoOut.model_validate(video)
    data.has_proxy = bool(video.proxy_path)
    data.has_thumbnail = bool(video.thumbnail_path)
    return data


async def _enqueue_analysis(db: Session, video: SourceVideo) -> ProcessingJob:
    job = ProcessingJob(
        project_id=video.project_id,
        source_video_id=video.id,
        job_type="analyze",
        status="pending",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    await job_queue.enqueue(job.id)
    return job


@router.get("", response_model=list[SourceVideoOut])
def list_videos(project_id: str, db: Session = Depends(get_db)) -> list[SourceVideoOut]:
    videos = (
        db.query(SourceVideo)
        .filter(SourceVideo.project_id == project_id)
        .order_by(SourceVideo.created_at.desc())
        .all()
    )
    return [_to_out(v) for v in videos]


@router.post("/import", response_model=list[SourceVideoOut])
async def import_videos(
    project_id: str,
    files: list[UploadFile],
    db: Session = Depends(get_db),
) -> list[SourceVideoOut]:
    settings = get_settings()
    results: list[SourceVideo] = []
    temp_dir = settings.storage_path / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for upload in files:
        import_service.validate_extension(upload.filename or "")
        temp_path = temp_dir / f"upload_{uuid.uuid4().hex}_{Path(upload.filename).name}"
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        written = 0
        with open(temp_path, "wb") as f:
            while chunk := await upload.read(CHUNK_SIZE):
                written += len(chunk)
                if written > max_bytes:
                    f.close()
                    temp_path.unlink(missing_ok=True)
                    raise InvalidFileError(f"Archivo excede el limite de {settings.max_upload_size_mb}MB")
                f.write(chunk)

        try:
            video = import_service.register_video_from_path(db, project_id, temp_path, move=True)
        finally:
            temp_path.unlink(missing_ok=True)

        results.append(video)
        if video.import_status == "ready":
            await _enqueue_analysis(db, video)

    return [_to_out(v) for v in results]


@router.post("/import-path", response_model=SourceVideoOut)
async def import_by_path(payload: ImportPathRequest, db: Session = Depends(get_db)) -> SourceVideoOut:
    video = import_service.register_video_from_path(db, payload.project_id, Path(payload.path), move=False)
    if video.import_status == "ready":
        await _enqueue_analysis(db, video)
    return _to_out(video)


@router.post("/import-folder", response_model=list[SourceVideoOut])
async def import_folder(payload: ImportFolderRequest, db: Session = Depends(get_db)) -> list[SourceVideoOut]:
    files = import_service.list_video_files_in_folder(Path(payload.folder_path))
    results = []
    for file_path in files:
        video = import_service.register_video_from_path(db, payload.project_id, file_path, move=False)
        results.append(video)
        if video.import_status == "ready":
            await _enqueue_analysis(db, video)
    return [_to_out(v) for v in results]


@router.get("/{video_id}", response_model=SourceVideoOut)
def get_video(video_id: str, db: Session = Depends(get_db)) -> SourceVideoOut:
    video = db.get(SourceVideo, video_id)
    if not video:
        raise NotFoundError("Video no encontrado")
    return _to_out(video)


def _stream_file_with_range(request: Request, file_path: Path, media_type: str) -> StreamingResponse | FileResponse:
    file_size = file_path.stat().st_size
    range_header = request.headers.get("range")

    if not range_header:
        return FileResponse(file_path, media_type=media_type)

    match = RANGE_RE.match(range_header)
    if not match:
        return FileResponse(file_path, media_type=media_type)

    start_str, end_str = match.groups()
    start = int(start_str) if start_str else 0
    end = int(end_str) if end_str else file_size - 1
    end = min(end, file_size - 1)
    length = end - start + 1

    def iterator():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = length
            while remaining > 0:
                chunk = f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
    }
    return StreamingResponse(iterator(), status_code=206, media_type=media_type, headers=headers)


@router.get("/{video_id}/stream")
def stream_video(video_id: str, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    video = db.get(SourceVideo, video_id)
    if not video:
        raise NotFoundError("Video no encontrado")
    file_path = settings.storage_path / video.storage_path
    if not file_path.exists():
        raise NotFoundError("Archivo de video no encontrado en disco")
    return _stream_file_with_range(request, file_path, media_type="video/mp4")


@router.get("/{video_id}/proxy")
def stream_proxy(video_id: str, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    video = db.get(SourceVideo, video_id)
    if not video or not video.proxy_path:
        raise NotFoundError("Proxy no disponible todavia")
    file_path = settings.storage_path / video.proxy_path
    if not file_path.exists():
        raise NotFoundError("Archivo de proxy no encontrado en disco")
    return _stream_file_with_range(request, file_path, media_type="video/mp4")


@router.get("/{video_id}/thumbnail")
def get_thumbnail(video_id: str, db: Session = Depends(get_db)):
    settings = get_settings()
    video = db.get(SourceVideo, video_id)
    if not video or not video.thumbnail_path:
        raise NotFoundError("Miniatura no disponible")
    file_path = settings.storage_path / video.thumbnail_path
    return FileResponse(file_path, media_type="image/jpeg")


@router.post("/{video_id}/analyze", response_model=dict)
async def analyze_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    video = db.get(SourceVideo, video_id)
    if not video:
        raise NotFoundError("Video no encontrado")
    job = await _enqueue_analysis(db, video)
    return {"job_id": job.id, "status": job.status}


@router.get("/{video_id}/analysis", response_model=VideoAnalysisOut)
def get_analysis(video_id: str, db: Session = Depends(get_db)) -> VideoAnalysisOut:
    video = db.get(SourceVideo, video_id)
    if not video:
        raise NotFoundError("Video no encontrado")
    transcript = db.query(Transcript).filter(Transcript.source_video_id == video_id).first()
    events = db.query(DetectedEvent).filter(DetectedEvent.source_video_id == video_id).all()
    clip_count = db.query(ClipCandidate).filter(ClipCandidate.source_video_id == video_id).count()
    return VideoAnalysisOut(
        video=_to_out(video),
        transcript=transcript,
        events=events,
        clip_count=clip_count,
    )


@router.delete("/{video_id}")
def delete_video(video_id: str, db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    video = db.get(SourceVideo, video_id)
    if not video:
        raise NotFoundError("Video no encontrado")
    for rel_path in (video.storage_path, video.proxy_path, video.thumbnail_path):
        if rel_path:
            p = settings.storage_path / rel_path
            if p.exists():
                p.unlink()
    db.delete(video)
    db.commit()
    return {"ok": True}
