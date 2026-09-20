from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    game_or_category: str | None = None
    target_platform: str = "tiktok"
    language: str = "es"


class ProjectUpdate(BaseModel):
    name: str | None = None
    game_or_category: str | None = None
    target_platform: str | None = None
    language: str | None = None
    ai_settings: dict | None = None
    status: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    game_or_category: str | None
    target_platform: str
    language: str
    ai_settings: dict
    status: str
    created_at: datetime
    updated_at: datetime
    video_count: int = 0
    clip_count: int = 0
