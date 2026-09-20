from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import UUIDPKMixin


class AppSetting(Base):
    __tablename__ = "app_setting"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AIProvider(Base, UUIDPKMixin):
    __tablename__ = "ai_provider"

    name: Mapped[str] = mapped_column(String(30), unique=True)
    api_base: Mapped[str | None] = mapped_column(default=None)
    model_name: Mapped[str | None] = mapped_column(default=None)
    requires_api_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


class Template(Base, UUIDPKMixin):
    __tablename__ = "template"

    name: Mapped[str]
    aspect_ratio: Mapped[str] = mapped_column(String(20), default="9:16")
    layout_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    creator_profile_id: Mapped[str | None] = mapped_column(default=None)


class GamePlugin(Base, UUIDPKMixin):
    __tablename__ = "game_plugin"

    game_key: Mapped[str] = mapped_column(String(50), unique=True)
    display_name: Mapped[str]
    detectors_json: Mapped[dict] = mapped_column(JSON, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
