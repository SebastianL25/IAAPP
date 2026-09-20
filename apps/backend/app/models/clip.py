from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class ClipCandidate(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "clip_candidate"

    project_id: Mapped[str] = mapped_column(ForeignKey("project.id"))
    source_video_id: Mapped[str] = mapped_column(ForeignKey("source_video.id"))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    viral_score: Mapped[int] = mapped_column(Integer, default=0)
    category: Mapped[str] = mapped_column(String(50), default="general")
    detected_events: Mapped[list] = mapped_column(JSON, default=list)
    hook: Mapped[str | None] = mapped_column(Text, default=None)
    reason: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    suggested_titles: Mapped[list] = mapped_column(JSON, default=list)
    suggested_hashtags: Mapped[list] = mapped_column(JSON, default=list)
    title: Mapped[str | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(String(20), default="candidate")  # candidate, approved, discarded

    project: Mapped["Project"] = relationship(back_populates="clip_candidates")  # noqa: F821
    versions: Mapped[list["ClipVersion"]] = relationship(
        back_populates="clip_candidate", cascade="all, delete-orphan"
    )
    feedback_entries: Mapped[list["UserFeedback"]] = relationship(  # noqa: F821
        back_populates="clip_candidate", cascade="all, delete-orphan"
    )


class ClipVersion(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "clip_version"

    clip_candidate_id: Mapped[str] = mapped_column(ForeignKey("clip_candidate.id"))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    aspect_ratio: Mapped[str] = mapped_column(String(20), default="9:16")
    template_id: Mapped[str | None] = mapped_column(default=None)
    caption_style_id: Mapped[str | None] = mapped_column(default=None)

    clip_candidate: Mapped["ClipCandidate"] = relationship(back_populates="versions")
    timeline: Mapped["Timeline | None"] = relationship(
        back_populates="clip_version", cascade="all, delete-orphan", uselist=False
    )
    export_jobs: Mapped[list["ExportJob"]] = relationship(  # noqa: F821
        back_populates="clip_version", cascade="all, delete-orphan"
    )


class Timeline(Base, UUIDPKMixin):
    __tablename__ = "timeline"

    clip_version_id: Mapped[str] = mapped_column(ForeignKey("clip_version.id"), unique=True)
    data_json: Mapped[dict] = mapped_column(JSON, default=dict)

    clip_version: Mapped["ClipVersion"] = relationship(back_populates="timeline")
    tracks: Mapped[list["TimelineTrack"]] = relationship(
        back_populates="timeline", cascade="all, delete-orphan"
    )


class TimelineTrack(Base, UUIDPKMixin):
    __tablename__ = "timeline_track"

    timeline_id: Mapped[str] = mapped_column(ForeignKey("timeline.id"))
    kind: Mapped[str] = mapped_column(String(20), default="video")
    order: Mapped[int] = mapped_column(Integer, default=0)

    timeline: Mapped["Timeline"] = relationship(back_populates="tracks")
    items: Mapped[list["TimelineItem"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )


class TimelineItem(Base, UUIDPKMixin):
    __tablename__ = "timeline_item"

    track_id: Mapped[str] = mapped_column(ForeignKey("timeline_track.id"))
    start_time: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)

    track: Mapped["TimelineTrack"] = relationship(back_populates="items")
