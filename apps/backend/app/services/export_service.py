from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.services import caption_service, ffmpeg_service

ASPECT_RATIO_RESOLUTIONS = {
    "9:16": (1080, 1920),
    "16:9": (1920, 1080),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
}

PRESET_SUFFIX = {
    "tiktok": "tiktok",
    "reels": "reels",
    "shorts": "shorts",
    "facebook": "facebook",
    "x": "x",
    "discord": "discord",
    "master": "master",
}


def resolve_resolution(aspect_ratio: str, custom: str | None = None) -> tuple[int, int]:
    if custom:
        w, h = custom.lower().split("x")
        return int(w), int(h)
    return ASPECT_RATIO_RESOLUTIONS.get(aspect_ratio, (1080, 1920))


def build_output_filename(project_name: str, clip_index: int, viral_score: int, ext: str = "mp4") -> str:
    safe_project = "".join(c for c in project_name.lower().replace(" ", "-") if c.isalnum() or c == "-")
    from datetime import date

    today = date.today().isoformat()
    return f"{safe_project}_{today}_clip-{clip_index:02d}_score-{viral_score}.{ext}"


def export_clip(
    source_video_path: Path,
    output_path: Path,
    start_time: float,
    end_time: float,
    aspect_ratio: str,
    fps: int | None,
    burn_captions: bool,
    transcript_segments: list[dict] | None,
    resolution_override: str | None = None,
) -> None:
    settings = get_settings()
    width, height = resolve_resolution(aspect_ratio, resolution_override)

    subtitles_path = None
    if burn_captions and transcript_segments:
        srt_content = caption_service.build_srt_for_range(transcript_segments, start_time, end_time)
        if srt_content.strip():
            subtitles_path = settings.storage_path / "temp" / f"{output_path.stem}.srt"
            caption_service.write_srt_file(srt_content, subtitles_path)

    ffmpeg_service.cut_and_reframe(
        source=source_video_path,
        dest=output_path,
        start_time=start_time,
        end_time=end_time,
        target_width=width,
        target_height=height,
        subtitles_path=subtitles_path,
        fps=fps,
    )
