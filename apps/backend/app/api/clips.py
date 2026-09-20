from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.session import get_db
from app.models.clip import ClipCandidate, ClipVersion
from app.models.feedback import UserFeedback
from app.models.job import ExportJob
from app.schemas.clip import (
    ClipCandidateOut,
    ClipCandidateUpdate,
    ClipExportRequest,
    ClipFeedbackRequest,
    ExportJobOut,
)
from app.services import export_service
from app.workers import job_queue

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.get("", response_model=list[ClipCandidateOut])
def list_clips(
    project_id: str | None = None,
    source_video_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[ClipCandidateOut]:
    query = db.query(ClipCandidate)
    if project_id:
        query = query.filter(ClipCandidate.project_id == project_id)
    if source_video_id:
        query = query.filter(ClipCandidate.source_video_id == source_video_id)
    if status:
        query = query.filter(ClipCandidate.status == status)
    return query.order_by(ClipCandidate.viral_score.desc()).all()


@router.get("/{clip_id}", response_model=ClipCandidateOut)
def get_clip(clip_id: str, db: Session = Depends(get_db)) -> ClipCandidateOut:
    clip = db.get(ClipCandidate, clip_id)
    if not clip:
        raise NotFoundError("Clip no encontrado")
    return clip


@router.patch("/{clip_id}", response_model=ClipCandidateOut)
def update_clip(clip_id: str, payload: ClipCandidateUpdate, db: Session = Depends(get_db)) -> ClipCandidateOut:
    clip = db.get(ClipCandidate, clip_id)
    if not clip:
        raise NotFoundError("Clip no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(clip, field, value)
    db.commit()
    db.refresh(clip)
    return clip


@router.post("/{clip_id}/approve", response_model=ClipCandidateOut)
def approve_clip(clip_id: str, payload: ClipFeedbackRequest | None = None, db: Session = Depends(get_db)) -> ClipCandidateOut:
    clip = db.get(ClipCandidate, clip_id)
    if not clip:
        raise NotFoundError("Clip no encontrado")
    clip.status = "approved"
    db.add(UserFeedback(clip_candidate_id=clip.id, label=(payload.label if payload else "approved"), notes=(payload.notes if payload else None)))
    db.commit()
    db.refresh(clip)
    return clip


@router.post("/{clip_id}/discard", response_model=ClipCandidateOut)
def discard_clip(clip_id: str, payload: ClipFeedbackRequest | None = None, db: Session = Depends(get_db)) -> ClipCandidateOut:
    clip = db.get(ClipCandidate, clip_id)
    if not clip:
        raise NotFoundError("Clip no encontrado")
    clip.status = "discarded"
    db.add(UserFeedback(clip_candidate_id=clip.id, label=(payload.label if payload else "discarded"), notes=(payload.notes if payload else None)))
    db.commit()
    db.refresh(clip)
    return clip


@router.post("/{clip_id}/export", response_model=ExportJobOut)
async def export_clip(clip_id: str, payload: ClipExportRequest, db: Session = Depends(get_db)) -> ExportJobOut:
    clip = db.get(ClipCandidate, clip_id)
    if not clip:
        raise NotFoundError("Clip no encontrado")

    version = ClipVersion(
        clip_candidate_id=clip.id,
        start_time=clip.start_time,
        end_time=clip.end_time,
        aspect_ratio=payload.aspect_ratio,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    width, height = export_service.resolve_resolution(payload.aspect_ratio, payload.resolution)
    export_job = ExportJob(
        clip_version_id=version.id,
        preset=payload.preset,
        resolution=f"{width}x{height}",
        fps=payload.fps or 30,
        status="queued",
    )
    db.add(export_job)
    db.commit()
    db.refresh(export_job)

    await job_queue.enqueue_export(export_job.id)
    return export_job
