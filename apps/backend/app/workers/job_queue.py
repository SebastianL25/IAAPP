"""Cola de trabajos local (sin Redis/Celery) para Fase 1.

El estado de cada trabajo vive en la tabla `processing_job` (SQLite), asi
que sobrevive a un reinicio del backend. La cola en memoria (`asyncio.Queue`)
solo orquesta la ejecucion mientras el proceso esta vivo; al arrancar,
`recover_pending_jobs` vuelve a encolar los pendientes.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.database.session import SessionLocal
from app.models.job import ExportJob, ProcessingJob
from app.websocket.manager import manager

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue()
_pause_event = asyncio.Event()
_pause_event.set()  # no pausado por defecto
_cancelled_jobs: set[str] = set()
_workers: list[asyncio.Task] = []


def is_cancelled(job_id: str) -> bool:
    return job_id in _cancelled_jobs


async def enqueue(job_id: str) -> None:
    """Encola un ProcessingJob (kind='analyze')."""
    await _queue.put(("analyze", job_id))


async def enqueue_export(export_job_id: str) -> None:
    await _queue.put(("export", export_job_id))


def update_progress(job_id: str, percent: float, message: str, status: str | None = None) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        job.progress_percent = percent
        job.stage_message = message
        if status:
            job.status = status
            if status == "running" and not job.started_at:
                job.started_at = datetime.now(timezone.utc).isoformat()
            if status in ("done", "error", "cancelled"):
                job.finished_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        payload = {
            "type": "job_progress",
            "job_id": job_id,
            "job_type": job.job_type,
            "status": job.status,
            "progress_percent": job.progress_percent,
            "stage_message": job.stage_message,
        }
        manager.broadcast_threadsafe(payload, project_id=job.project_id)
    finally:
        db.close()


def mark_error(job_id: str, error_message: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(ProcessingJob, job_id)
        if not job:
            return
        job.status = "error"
        job.error_message = error_message[:1000]
        job.finished_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        manager.broadcast_threadsafe(
            {
                "type": "job_progress",
                "job_id": job_id,
                "job_type": job.job_type,
                "status": "error",
                "progress_percent": job.progress_percent,
                "stage_message": error_message[:200],
            },
            project_id=job.project_id,
        )
    finally:
        db.close()


def update_export_progress(export_job_id: str, percent: float, status: str | None = None) -> None:
    db = SessionLocal()
    try:
        job = db.get(ExportJob, export_job_id)
        if not job:
            return
        job.progress_percent = percent
        if status:
            job.status = status
            if status in ("done", "error", "cancelled"):
                job.finished_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        manager.broadcast_threadsafe(
            {
                "type": "export_progress",
                "job_id": export_job_id,
                "status": job.status,
                "progress_percent": job.progress_percent,
            }
        )
    finally:
        db.close()


def mark_export_error(export_job_id: str, error_message: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(ExportJob, export_job_id)
        if not job:
            return
        job.status = "error"
        job.error_message = error_message[:1000]
        job.finished_at = datetime.now(timezone.utc).isoformat()
        db.commit()
        manager.broadcast_threadsafe(
            {"type": "export_progress", "job_id": export_job_id, "status": "error", "progress_percent": job.progress_percent}
        )
    finally:
        db.close()


async def _worker_loop(worker_name: str) -> None:
    from app.workers import pipeline  # import diferido para evitar ciclos

    while True:
        kind, job_id = await _queue.get()
        await _pause_event.wait()
        if job_id in _cancelled_jobs:
            _cancelled_jobs.discard(job_id)
            if kind == "analyze":
                update_progress(job_id, 0, "Cancelado antes de iniciar", status="cancelled")
            else:
                update_export_progress(job_id, 0, status="cancelled")
            _queue.task_done()
            continue
        try:
            logger.info("[%s] procesando job (%s) %s", worker_name, kind, job_id)
            if kind == "analyze":
                await asyncio.to_thread(pipeline.run_job, job_id)
            else:
                await asyncio.to_thread(pipeline.run_export_job, job_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error ejecutando job %s", job_id)
            if kind == "analyze":
                mark_error(job_id, str(exc))
            else:
                mark_export_error(job_id, str(exc))
        finally:
            _cancelled_jobs.discard(job_id)
            _queue.task_done()


def start_workers(loop: asyncio.AbstractEventLoop, count: int = 1) -> None:
    manager.set_loop(loop)
    for i in range(max(1, count)):
        task = loop.create_task(_worker_loop(f"worker-{i}"))
        _workers.append(task)


def pause_queue() -> None:
    _pause_event.clear()


def resume_queue() -> None:
    _pause_event.set()


def cancel_job(job_id: str) -> None:
    _cancelled_jobs.add(job_id)


async def recover_pending_jobs() -> None:
    """Al arrancar: los jobs que quedaron `running` se marcan error
    (el proceso que los ejecutaba murio); los `pending` se reencolan."""
    db = SessionLocal()
    try:
        stuck = db.query(ProcessingJob).filter(ProcessingJob.status == "running").all()
        for job in stuck:
            job.status = "error"
            job.error_message = "Interrumpido por reinicio del servidor"
        pending = db.query(ProcessingJob).filter(ProcessingJob.status == "pending").all()

        stuck_exports = db.query(ExportJob).filter(ExportJob.status == "running").all()
        for job in stuck_exports:
            job.status = "error"
            job.error_message = "Interrumpido por reinicio del servidor"
        pending_exports = db.query(ExportJob).filter(ExportJob.status == "queued").all()

        db.commit()
        for job in pending:
            await enqueue(job.id)
        for job in pending_exports:
            await enqueue_export(job.id)
        if stuck or pending or stuck_exports or pending_exports:
            logger.info(
                "Recuperados %d jobs pendientes (%d exports), %d marcados error (%d exports)",
                len(pending), len(pending_exports), len(stuck), len(stuck_exports),
            )
    finally:
        db.close()
