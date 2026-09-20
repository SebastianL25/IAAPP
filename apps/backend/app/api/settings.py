from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_db
from app.models.settings import AppSetting
from app.schemas.settings import AppSettingsOut, AppSettingsUpdate
from app.services.clip_detection_service import DEFAULT_WEIGHTS

router = APIRouter(prefix="/api/settings", tags=["settings"])

DEFAULTS = {
    "ai_provider": None,  # None -> usa el de .env
    "cloud_processing_enabled": False,
    "default_sensitivity": "equilibrado",
    "max_parallel_jobs": 1,
    "score_weights": DEFAULT_WEIGHTS,
}


def _get_all(db: Session) -> dict:
    rows = {row.key: row.value_json for row in db.query(AppSetting).all()}
    merged = {**DEFAULTS, **rows}
    return merged


@router.get("", response_model=AppSettingsOut)
def get_settings_endpoint(db: Session = Depends(get_db)) -> AppSettingsOut:
    env_settings = get_settings()
    merged = _get_all(db)
    if not merged.get("ai_provider"):
        merged["ai_provider"] = env_settings.ai_provider
    return AppSettingsOut(**merged)


@router.put("", response_model=AppSettingsOut)
def update_settings_endpoint(payload: AppSettingsUpdate, db: Session = Depends(get_db)) -> AppSettingsOut:
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        row = db.get(AppSetting, key)
        if row:
            row.value_json = value
        else:
            db.add(AppSetting(key=key, value_json=value))
    db.commit()
    return get_settings_endpoint(db)
