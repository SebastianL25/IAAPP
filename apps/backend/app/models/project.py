from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Project(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "project"

    name: Mapped[str]
    game_or_category: Mapped[str | None] = mapped_column(default=None)
    target_platform: Mapped[str] = mapped_column(default="tiktok")
    language: Mapped[str] = mapped_column(default="es")
    ai_settings: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "sensitivity": "equilibrado",
            "scene_threshold": 0.35,
            "ai_provider": None,
        },
    )
    template_id: Mapped[str | None] = mapped_column(default=None)
    creator_profile_id: Mapped[str | None] = mapped_column(
        ForeignKey("creator_profile.id"), default=None
    )
    status: Mapped[str] = mapped_column(String(20), default="active")  # active, archived, trashed

    source_videos: Mapped[list["SourceVideo"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    clip_candidates: Mapped[list["ClipCandidate"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
