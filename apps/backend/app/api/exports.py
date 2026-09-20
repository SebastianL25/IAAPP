from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.database.session import get_db
from app.models.clip import ClipVersion
from app.models.job import ExportJob
from app.schemas.clip import ExportJobOut

router = APIRouter(prefix="/api/exports", tags=["exports"])


@router.get("", response_model=list[ExportJobOut])
def list_exports(clip_id: str | None = None, db: Session = Depends(get_db)) -> list[ExportJobOut]:
    query = db.query(ExportJob)
    if clip_id:
        query = query.join(ClipVersion, ExportJob.clip_version_id == ClipVersion.id).filter(
            ClipVersion.clip_candidate_id == clip_id
        )
    return query.order_by(ExportJob.created_at.desc()).all()


@router.get("/{export_id}", response_model=ExportJobOut)
def get_export(export_id: str, db: Session = Depends(get_db)) -> ExportJobOut:
    job = db.get(ExportJob, export_id)
    if not job:
        raise NotFoundError("Exportacion no encontrada")
    return job


@router.get("/{export_id}/download")
def download_export(export_id: str, db: Session = Depends(get_db)):
    settings = get_settings()
    job = db.get(ExportJob, export_id)
    if not job or not job.output_path:
        raise NotFoundError("Archivo exportado no disponible")
    file_path = settings.storage_path / job.output_path
    if not file_path.exists():
        raise NotFoundError("Archivo exportado no encontrado en disco")
    return FileResponse(file_path, media_type="video/mp4", filename=file_path.name)
