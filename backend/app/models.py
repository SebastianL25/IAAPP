from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Format = Literal["9:16", "1:1", "16:9"]
StreamType = Literal["screen_cam", "cam_only"]


class CropRect(BaseModel):
    """Rectángulo normalizado (0..1) relativo al video original."""

    x: float = 0.0
    y: float = 0.0
    w: float = 1.0
    h: float = 1.0


class ClipConfig(BaseModel):
    id: str
    start: float
    end: float
    format: Format = "9:16"
    stream_type: StreamType = "screen_cam"
    camera_rect: CropRect = Field(default_factory=lambda: CropRect(x=0.0, y=0.0, w=0.35, h=0.35))
    content_rect: CropRect = Field(default_factory=lambda: CropRect(x=0.0, y=0.0, w=1.0, h=1.0))
    keep_full_vertical_game: bool = False
    audio_sync_ms: int = 0
    subtitles_enabled: bool = True
    subtitles: list[dict] = Field(default_factory=list)  # [{start,end,text}]
    mute_intervals: list[list[float]] = Field(default_factory=list)  # [[start,end], ...] tiempo local del clip
    kick_username: str = ""
    score: Optional[float] = None
    reasons: list[str] = Field(default_factory=list)
    export_status: Literal["idle", "queued", "processing", "done", "error", "cancelled"] = "idle"
    export_progress: float = 0.0
    export_path: Optional[str] = None
    export_error: Optional[str] = None


class ProjectConfig(BaseModel):
    format: Format = "9:16"
    clip_duration: float = 30.0
    clip_count: int = 5
    stream_type: StreamType = "screen_cam"
    camera_rect: CropRect = Field(default_factory=lambda: CropRect(x=0.0, y=0.0, w=0.35, h=0.35))
    kick_username: str = ""
    subtitles_enabled: bool = True


class Project(BaseModel):
    id: str
    video_id: str
    original_filename: str
    duration: float
    width: int
    height: int
    fps: float
    config: ProjectConfig
    clips: list[ClipConfig] = Field(default_factory=list)
    analysis_status: Literal["idle", "queued", "processing", "done", "error", "cancelled"] = "idle"
    analysis_job_id: Optional[str] = None
    created_at: str
