from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class CreatorProfile(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "creator_profile"

    display_name: Mapped[str] = mapped_column(default="xSlou")
    content_types: Mapped[list] = mapped_column(JSON, default=list)
    logo_path: Mapped[str | None] = mapped_column(default=None)
    brand_colors: Mapped[dict] = mapped_column(JSON, default=dict)
    fonts: Mapped[dict] = mapped_column(JSON, default=dict)
    social_links: Mapped[dict] = mapped_column(JSON, default=dict)
    watermark_path: Mapped[str | None] = mapped_column(default=None)
    default_facecam_position: Mapped[str | None] = mapped_column(default=None)
    preferred_duration: Mapped[int | None] = mapped_column(default=None)
    preferred_platforms: Mapped[list] = mapped_column(JSON, default=list)
