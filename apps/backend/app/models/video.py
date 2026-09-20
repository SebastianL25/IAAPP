from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class SourceVideo(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "source_video"
    __table_args__ = (UniqueConstraint("project_id", "file_hash", name="uq_project_hash"),)

    project_id: Mapped[str] = mapped_column(ForeignKey("project.id"))
    original_filename: Mapped[str]
    storage_path: Mapped[str]
    proxy_path: Mapped[str | None] = mapped_column(default=None)
    thumbnail_path: Mapped[str | None] = mapped_column(default=None)
    file_hash: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(default=0)
    import_status: Mapped[str] = mapped_column(String(20), default="pending")
    error_message: Mapped[str | None] = mapped_column(default=None)

    project: Mapped["Project"] = relationship(back_populates="source_videos")  # noqa: F821
    video_metadata: Mapped["VideoMetadata | None"] = relationship(
        back_populates="source_video", cascade="all, delete-orphan", uselist=False
    )
    transcript: Mapped["Transcript | None"] = relationship(
        back_populates="source_video", cascade="all, delete-orphan", uselist=False
    )
    detected_events: Mapped[list["DetectedEvent"]] = relationship(
        back_populates="source_video", cascade="all, delete-orphan"
    )


class VideoMetadata(Base, UUIDPKMixin):
    __tablename__ = "video_metadata"

    source_video_id: Mapped[str] = mapped_column(ForeignKey("source_video.id"), unique=True)
    duration_seconds: Mapped[float] = mapped_column(Float, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    fps: Mapped[float] = mapped_column(Float, default=0)
    video_codec: Mapped[str | None] = mapped_column(default=None)
    audio_codec: Mapped[str | None] = mapped_column(default=None)
    bitrate: Mapped[int] = mapped_column(Integer, default=0)
    audio_channels: Mapped[int] = mapped_column(Integer, default=0)
    raw_probe_json: Mapped[dict] = mapped_column(JSON, default=dict)

    source_video: Mapped["SourceVideo"] = relationship(back_populates="video_metadata")


class Transcript(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "transcript"

    source_video_id: Mapped[str] = mapped_column(ForeignKey("source_video.id"), unique=True)
    language: Mapped[str | None] = mapped_column(default=None)
    engine: Mapped[str] = mapped_column(default="faster-whisper")
    model_size: Mapped[str] = mapped_column(default="small")
    full_text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="pending")

    source_video: Mapped["SourceVideo"] = relationship(back_populates="transcript")
    segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="transcript", cascade="all, delete-orphan", order_by="TranscriptSegment.start_time"
    )


class TranscriptSegment(Base, UUIDPKMixin):
    __tablename__ = "transcript_segment"

    transcript_id: Mapped[str] = mapped_column(ForeignKey("transcript.id"))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    words_json: Mapped[list] = mapped_column(JSON, default=list)

    transcript: Mapped["Transcript"] = relationship(back_populates="segments")


class DetectedEvent(Base, UUIDPKMixin):
    __tablename__ = "detected_event"

    source_video_id: Mapped[str] = mapped_column(ForeignKey("source_video.id"))
    event_type: Mapped[str] = mapped_column(String(50))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source: Mapped[str] = mapped_column(String(30), default="audio")

    source_video: Mapped["SourceVideo"] = relationship(back_populates="detected_events")
