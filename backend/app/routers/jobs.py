from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import jobs as jobs_module

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/{job_id}")
def get_job(job_id: str):
    job = jobs_module.get_job(job_id)
    if not job:
        raise HTTPException(404, "Trabajo no encontrado")
    return job.to_public()


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    ok = jobs_module.cancel_job(job_id)
    if not ok:
        raise HTTPException(404, "Trabajo no encontrado")
    return {"ok": True}


@router.get("")
def list_jobs(project_id: str | None = None):
    return [j.to_public() for j in jobs_module.list_jobs(project_id)]
