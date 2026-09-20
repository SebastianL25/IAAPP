from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ClipCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    source_video_id: str
    start_time: float
    end_time: float
    viral_score: int
    category: str
    detected_events: list
    hook: str | None
    reason: str
    confidence: float
    title: str | None
    status: str
    created_at: datetime


class ClipCandidateUpdate(BaseModel):
    start_time: float | None = None
    end_time: float | None = None
    title: str | None = None


class ClipFeedbackRequest(BaseModel):
    label: str
    notes: str | None = None


class ClipExportRequest(BaseModel):
    aspect_ratio: str = "9:16"
    preset: str = "tiktok"
    burn_captions: bool = True
    resolution: str | None = None
    fps: int | None = None


class ExportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clip_version_id: str
    preset: str
    resolution: str
    fps: int
    status: str
    progress_percent: float
    output_path: str | None
    error_message: str | None
