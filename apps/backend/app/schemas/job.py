from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProcessingJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str | None
    source_video_id: str | None
    job_type: str
    status: str
    progress_percent: float
    stage_message: str
    error_message: str | None
    created_at: datetime
