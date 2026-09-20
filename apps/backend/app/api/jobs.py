from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.session import get_db
from app.models.job import ProcessingJob
from app.schemas.job import ProcessingJobOut
from app.workers import job_queue

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[ProcessingJobOut])
def list_jobs(
    project_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
) -> list[ProcessingJobOut]:
    query = db.query(ProcessingJob)
    if project_id:
        query = query.filter(ProcessingJob.project_id == project_id)
    if status:
        query = query.filter(ProcessingJob.status == status)
    return query.order_by(ProcessingJob.created_at.desc()).all()


@router.get("/{job_id}", response_model=ProcessingJobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> ProcessingJobOut:
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise NotFoundError("Trabajo no encontrado")
    return job


@router.post("/pause-queue")
def pause_queue() -> dict:
    job_queue.pause_queue()
    return {"ok": True, "paused": True}


@router.post("/resume-queue")
def resume_queue() -> dict:
    job_queue.resume_queue()
    return {"ok": True, "paused": False}


@router.post("/{job_id}/pause")
def pause_job(job_id: str) -> dict:
    # Fase 1: la pausa fina por-job no esta soportada (ffmpeg/whisper no son
    # pausables a mitad de ejecucion); se pausa la cola completa.
    job_queue.pause_queue()
    return {"ok": True, "message": "Cola pausada (pausa por-job llega en Fase 2)"}


@router.post("/{job_id}/resume")
def resume_job(job_id: str) -> dict:
    job_queue.resume_queue()
    return {"ok": True}


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise NotFoundError("Trabajo no encontrado")
    job_queue.cancel_job(job_id)
    if job.status == "pending":
        job.status = "cancelled"
        db.commit()
    return {"ok": True}


@router.post("/{job_id}/retry")
async def retry_job(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(ProcessingJob, job_id)
    if not job:
        raise NotFoundError("Trabajo no encontrado")
    job.status = "pending"
    job.progress_percent = 0
    job.error_message = None
    job.stage_message = "Reintentando..."
    db.commit()
    await job_queue.enqueue(job.id)
    return {"ok": True}
