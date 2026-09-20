from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.settings import Template

router = APIRouter(prefix="/api/templates", tags=["templates"])

BUILTIN_TEMPLATES = [
    {"name": "Juego completo + facecam superior", "aspect_ratio": "9:16", "layout_json": {"facecam": "top"}},
    {"name": "Juego completo + facecam inferior", "aspect_ratio": "9:16", "layout_json": {"facecam": "bottom"}},
    {"name": "Facecam flotante", "aspect_ratio": "9:16", "layout_json": {"facecam": "floating"}},
    {"name": "Facecam circular", "aspect_ratio": "9:16", "layout_json": {"facecam": "circle"}},
    {"name": "Facecam con borde", "aspect_ratio": "9:16", "layout_json": {"facecam": "bordered"}},
    {"name": "Gameplay arriba / facecam abajo", "aspect_ratio": "9:16", "layout_json": {"split": "gameplay_top"}},
    {"name": "Facecam arriba / gameplay abajo", "aspect_ratio": "9:16", "layout_json": {"split": "facecam_top"}},
    {"name": "Gameplay desenfocado de fondo", "aspect_ratio": "9:16", "layout_json": {"background": "blur"}},
    {"name": "Pantalla dividida", "aspect_ratio": "9:16", "layout_json": {"split": "side_by_side"}},
    {"name": "Solo gameplay", "aspect_ratio": "9:16", "layout_json": {"facecam": "none"}},
    {"name": "Solo facecam", "aspect_ratio": "9:16", "layout_json": {"gameplay": "none"}},
    {"name": "Reaccion", "aspect_ratio": "9:16", "layout_json": {"layout": "reaction"}},
    {"name": "Podcast", "aspect_ratio": "9:16", "layout_json": {"layout": "podcast"}},
    {"name": "Just Chatting", "aspect_ratio": "9:16", "layout_json": {"layout": "just_chatting"}},
]


class TemplateCreate(BaseModel):
    name: str
    aspect_ratio: str = "9:16"
    layout_json: dict = {}


def _seed_builtin_templates(db: Session) -> None:
    if db.query(Template).filter(Template.is_builtin.is_(True)).count() > 0:
        return
    for t in BUILTIN_TEMPLATES:
        db.add(Template(name=t["name"], aspect_ratio=t["aspect_ratio"], layout_json=t["layout_json"], is_builtin=True))
    db.commit()


@router.get("")
def list_templates(db: Session = Depends(get_db)) -> list[dict]:
    _seed_builtin_templates(db)
    templates = db.query(Template).order_by(Template.is_builtin.desc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "aspect_ratio": t.aspect_ratio,
            "layout_json": t.layout_json,
            "is_builtin": t.is_builtin,
        }
        for t in templates
    ]


@router.post("")
def create_template(payload: TemplateCreate, db: Session = Depends(get_db)) -> dict:
    template = Template(name=payload.name, aspect_ratio=payload.aspect_ratio, layout_json=payload.layout_json, is_builtin=False)
    db.add(template)
    db.commit()
    db.refresh(template)
    return {"id": template.id, "name": template.name, "aspect_ratio": template.aspect_ratio, "layout_json": template.layout_json}
