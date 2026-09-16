"""Gestor de trabajos en segundo plano con progreso, cancelación y persistencia en disco."""
from __future__ import annotations

import json
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from . import config

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="xslou-job")
_jobs: dict[str, "Job"] = {}
_lock = threading.Lock()


@dataclass
class Job:
    id: str
    type: str
    project_id: Optional[str]
    extra: dict[str, Any] = field(default_factory=dict)
    status: str = "queued"  # queued, processing, done, error, cancelled
    stage: str = "En cola"
    progress: float = 0.0
    error: Optional[str] = None
    started_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    cancel_event: threading.Event = field(default_factory=threading.Event, repr=False)
    result: Optional[dict] = None

    def eta_seconds(self) -> Optional[float]:
        if self.progress <= 0.02 or self.status != "processing":
            return None
        elapsed = time.time() - self.started_at
        remaining = elapsed * (1 - self.progress) / self.progress
        return max(0.0, remaining)

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "project_id": self.project_id,
            "extra": self.extra,
            "status": self.status,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "error": self.error,
            "elapsed_seconds": round(time.time() - self.started_at, 1),
            "eta_seconds": self.eta_seconds(),
            "result": self.result,
        }

    def persist(self) -> None:
        try:
            path = config.JOBS_DIR / f"{self.id}.json"
            tmp = path.with_suffix(f".tmp{self.id}")
            tmp.write_text(json.dumps(self.to_public(), ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
        except Exception:
            pass


def _log_path(job_id: str):
    return config.LOGS_DIR / f"{job_id}.log"


def get_job(job_id: str) -> Optional[Job]:
    with _lock:
        return _jobs.get(job_id)


def list_jobs(project_id: Optional[str] = None) -> list[Job]:
    with _lock:
        jobs = list(_jobs.values())
    if project_id:
        jobs = [j for j in jobs if j.project_id == project_id]
    jobs.sort(key=lambda j: j.started_at, reverse=True)
    return jobs


def cancel_job(job_id: str) -> bool:
    job = get_job(job_id)
    if not job:
        return False
    job.cancel_event.set()
    return True


class ProgressReporter:
    def __init__(self, job: Job):
        self._job = job

    def stage(self, text: str) -> None:
        self._job.stage = text
        self._job.updated_at = time.time()
        self._job.persist()

    def progress(self, frac: float) -> None:
        self._job.progress = max(0.0, min(1.0, frac))
        self._job.updated_at = time.time()
        self._job.persist()

    @property
    def cancel_event(self) -> threading.Event:
        return self._job.cancel_event


def submit(
    job_type: str,
    project_id: Optional[str],
    fn: Callable[[ProgressReporter], dict | None],
    extra: Optional[dict] = None,
    job_id: Optional[str] = None,
) -> str:
    job = Job(id=job_id or _new_id(), type=job_type, project_id=project_id, extra=extra or {})
    with _lock:
        _jobs[job.id] = job
    job.persist()

    def _run():
        job.status = "processing"
        reporter = ProgressReporter(job)
        log_path = _log_path(job.id)
        try:
            result = fn(reporter)
            if job.cancel_event.is_set():
                job.status = "cancelled"
                job.stage = "Cancelado"
            else:
                job.status = "done"
                job.stage = "Completado"
                job.progress = 1.0
                job.result = result
        except InterruptedError:
            job.status = "cancelled"
            job.stage = "Cancelado"
        except Exception as exc:  # noqa: BLE001
            job.status = "error"
            job.stage = "Error"
            job.error = str(exc)
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(traceback.format_exc())
            except Exception:
                pass
        finally:
            job.finished_at = time.time()
            job.persist()

    _executor.submit(_run)
    return job.id


def _new_id() -> str:
    import uuid

    return uuid.uuid4().hex[:12]
