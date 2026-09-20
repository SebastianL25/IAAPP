from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class UserFeedback(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "user_feedback"

    clip_candidate_id: Mapped[str] = mapped_column(ForeignKey("clip_candidate.id"))
    label: Mapped[str] = mapped_column(String(30))
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    clip_candidate: Mapped["ClipCandidate"] = relationship(back_populates="feedback_entries")  # noqa: F821


class CaptionStyle(Base, UUIDPKMixin):
    __tablename__ = "caption_style"

    name: Mapped[str]
    font: Mapped[str] = mapped_column(default="Arial")
    size: Mapped[int] = mapped_column(default=48)
    color: Mapped[str] = mapped_column(default="#FFFFFF")
    highlight_color: Mapped[str] = mapped_column(default="#FFD400")
    position: Mapped[str] = mapped_column(default="bottom")
    style_preset: Mapped[str] = mapped_column(default="minimal")
    config_json: Mapped[dict] = mapped_column(JSON, default=dict)
