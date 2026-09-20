from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.database.session import get_db
from app.models.clip import ClipCandidate
from app.models.project import Project
from app.models.video import SourceVideo
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _to_out(db: Session, project: Project) -> ProjectOut:
    video_count = db.query(func.count(SourceVideo.id)).filter(SourceVideo.project_id == project.id).scalar()
    clip_count = db.query(func.count(ClipCandidate.id)).filter(ClipCandidate.project_id == project.id).scalar()
    data = ProjectOut.model_validate(project)
    data.video_count = video_count or 0
    data.clip_count = clip_count or 0
    return data


@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    project = Project(**payload.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_out(db, project)


@router.get("", response_model=list[ProjectOut])
def list_projects(
    status: str | None = None,
    q: str | None = None,
    game: str | None = None,
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    query = db.query(Project)
    if status:
        query = query.filter(Project.status == status)
    else:
        query = query.filter(Project.status != "trashed")
    if q:
        query = query.filter(Project.name.ilike(f"%{q}%"))
    if game:
        query = query.filter(Project.game_or_category == game)
    projects = query.order_by(Project.updated_at.desc()).all()
    return [_to_out(db, p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectOut:
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Proyecto no encontrado")
    return _to_out(db, project)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: str, payload: ProjectUpdate, db: Session = Depends(get_db)) -> ProjectOut:
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Proyecto no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _to_out(db, project)


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)) -> dict:
    project = db.get(Project, project_id)
    if not project:
        raise NotFoundError("Proyecto no encontrado")
    project.status = "trashed"
    db.commit()
    return {"ok": True}
