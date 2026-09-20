from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.services import ffmpeg_service


def build_proxy_path(video_id: str) -> Path:
    settings = get_settings()
    return settings.storage_path / "proxies" / f"{video_id}.mp4"


def ensure_proxy(video_id: str, source_path: Path) -> Path:
    dest = build_proxy_path(video_id)
    if not dest.exists():
        ffmpeg_service.generate_proxy(source_path, dest, height=480)
    return dest
