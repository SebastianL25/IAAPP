from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ProcessingJob(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "processing_job"

    project_id: Mapped[str | None] = mapped_column(ForeignKey("project.id"), default=None)
    source_video_id: Mapped[str | None] = mapped_column(ForeignKey("source_video.id"), default=None)
    job_type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    stage_message: Mapped[str] = mapped_column(default="")
    error_message: Mapped[str | None] = mapped_column(default=None)
    started_at: Mapped[str | None] = mapped_column(default=None)
    finished_at: Mapped[str | None] = mapped_column(default=None)


class ExportJob(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "export_job"

    clip_version_id: Mapped[str] = mapped_column(ForeignKey("clip_version.id"))
    preset: Mapped[str] = mapped_column(String(30), default="tiktok")
    resolution: Mapped[str] = mapped_column(String(20), default="1080x1920")
    fps: Mapped[int] = mapped_column(default=30)
    codec: Mapped[str] = mapped_column(String(20), default="h264")
    status: Mapped[str] = mapped_column(String(20), default="queued")
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    output_path: Mapped[str | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(default=None)
    finished_at: Mapped[str | None] = mapped_column(default=None)

    clip_version: Mapped["ClipVersion"] = relationship(back_populates="export_jobs")  # noqa: F821
