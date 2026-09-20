from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VideoMetadataOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    duration_seconds: float
    width: int
    height: int
    fps: float
    video_codec: str | None
    audio_codec: str | None
    bitrate: int
    audio_channels: int


class SourceVideoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    original_filename: str
    file_hash: str
    size_bytes: int
    import_status: str
    error_message: str | None
    created_at: datetime
    video_metadata: VideoMetadataOut | None = None
    has_proxy: bool = False
    has_thumbnail: bool = False


class ImportPathRequest(BaseModel):
    project_id: str
    path: str


class ImportFolderRequest(BaseModel):
    project_id: str
    folder_path: str


class DetectedEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    start_time: float
    end_time: float
    confidence: float
    metadata_json: dict
    source: str


class TranscriptSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    start_time: float
    end_time: float
    text: str


class TranscriptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    language: str | None
    status: str
    full_text: str
    segments: list[TranscriptSegmentOut] = []


class VideoAnalysisOut(BaseModel):
    video: SourceVideoOut
    transcript: TranscriptOut | None
    events: list[DetectedEventOut]
    clip_count: int
