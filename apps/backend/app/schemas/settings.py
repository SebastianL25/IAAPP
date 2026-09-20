from pydantic import BaseModel


class AppSettingsOut(BaseModel):
    ai_provider: str
    cloud_processing_enabled: bool
    default_sensitivity: str
    max_parallel_jobs: int
    score_weights: dict


class AppSettingsUpdate(BaseModel):
    ai_provider: str | None = None
    cloud_processing_enabled: bool | None = None
    default_sensitivity: str | None = None
    max_parallel_jobs: int | None = None
    score_weights: dict | None = None
