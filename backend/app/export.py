"""Construcción del filtergraph de ffmpeg y exportación final de un clip."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Optional

from . import ffmpeg_utils
from .ffmpeg_utils import FORMAT_RESOLUTIONS, ProbeResult, build_mute_filter, build_sync_filter
from .models import ClipConfig, ProjectConfig
from .subtitles import blocks_to_ass


def _escape_path_for_filter(path: Path) -> str:
    p = str(path).replace("\\", "/")
    p = p.replace(":", "\\:")
    return p


_FONT_CANDIDATES = [
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _find_font() -> Optional[str]:
    for c in _FONT_CANDIDATES:
        if Path(c).exists():
            return c
    return None


def _crop_expr(rect, src_w: int, src_h: int) -> tuple[int, int, int, int]:
    w = max(2, round(rect.w * src_w))
    h = max(2, round(rect.h * src_h))
    x = max(0, min(src_w - w, round(rect.x * src_w)))
    y = max(0, min(src_h - h, round(rect.y * src_h)))
    return w, h, x, y


def build_video_filtergraph(clip: ClipConfig, probe: ProbeResult, out_w: int, out_h: int) -> tuple[str, str]:
    """Devuelve (filter_complex, label_de_salida_de_video) sin subtítulos ni marca de agua."""
    src_w, src_h = probe.width, probe.height
    filters: list[str] = []

    if clip.keep_full_vertical_game:
        filters.append("[0:v]split=2[bg_src][fg_src]")
        filters.append(
            f"[bg_src]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
            f"crop={out_w}:{out_h},boxblur=20:2[bg]"
        )
        filters.append(f"[fg_src]scale={out_w}:{out_h}:force_original_aspect_ratio=decrease[fg]")
        filters.append("[bg][fg]overlay=(W-w)/2:(H-h)/2[stacked]")
        return ";".join(filters), "[stacked]"

    if clip.stream_type == "cam_only":
        cw, ch, cx, cy = _crop_expr(clip.camera_rect, src_w, src_h)
        filters.append(f"[0:v]crop={cw}:{ch}:{cx}:{cy}[cam_src]")
        filters.append(
            f"[cam_src]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,crop={out_w}:{out_h}[stacked]"
        )
        return ";".join(filters), "[stacked]"

    # screen_cam: cámara arriba, contenido abajo
    top_h = out_h // 2
    bottom_h = out_h - top_h
    cw, ch, cx, cy = _crop_expr(clip.camera_rect, src_w, src_h)
    filters.append(f"[0:v]crop={cw}:{ch}:{cx}:{cy}[cam_src]")
    filters.append(
        f"[cam_src]scale={out_w}:{top_h}:force_original_aspect_ratio=increase,crop={out_w}:{top_h}[cam_top]"
    )
    ow, oh, ox, oy = _crop_expr(clip.content_rect, src_w, src_h)
    filters.append(f"[0:v]crop={ow}:{oh}:{ox}:{oy}[content_src]")
    filters.append(
        f"[content_src]scale={out_w}:{bottom_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{bottom_h}[content_bottom]"
    )
    filters.append("[cam_top][content_bottom]vstack=2[stacked]")
    return ";".join(filters), "[stacked]"


def export_clip(
    project_config: ProjectConfig,
    clip: ClipConfig,
    probe: ProbeResult,
    source_path: Path,
    ass_path: Optional[Path],
    out_path: Path,
    mute_intervals: Optional[list[tuple[float, float]]] = None,
    on_progress: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    log_path: Optional[Path] = None,
) -> None:
    out_w, out_h = FORMAT_RESOLUTIONS[clip.format]
    filter_complex, video_label = build_video_filtergraph(clip, probe, out_w, out_h)

    stages = [f"{filter_complex}"]
    current_label = video_label

    if ass_path is not None:
        ass_escaped = _escape_path_for_filter(ass_path)
        stages.append(f"{current_label}ass='{ass_escaped}'[subbed]")
        current_label = "[subbed]"

    if project_config.kick_username or clip.kick_username:
        username = clip.kick_username or project_config.kick_username
        watermark_text = f"KICK.COM/{username.upper()}"
        font = _find_font()
        fontfile_part = f"fontfile='{_escape_path_for_filter(Path(font))}':" if font else ""
        stages.append(
            f"{current_label}drawtext={fontfile_part}text='{watermark_text}':fontsize={max(20, out_h // 40)}:"
            f"fontcolor=white:borderw=2:bordercolor=black@0.8:x=(w-text_w)/2:y=h-th-{max(20, out_h // 30)}[wm]"
        )
        current_label = "[wm]"

    final_video_label = current_label.strip("[]")
    filter_complex_full = ";".join(stages)

    audio_filter_parts = [build_sync_filter(clip.audio_sync_ms)]
    mute_filter = build_mute_filter(mute_intervals or [])
    if mute_filter != "anull":
        audio_filter_parts.append(mute_filter)
    audio_filter = ",".join(audio_filter_parts)

    duration = clip.end - clip.start
    coarse_seek = max(0.0, clip.start - 15.0)
    fine_seek = clip.start - coarse_seek

    args = [
        "-ss", f"{coarse_seek:.3f}",
        "-i", str(source_path),
        "-ss", f"{fine_seek:.3f}",
        "-t", f"{duration:.3f}",
        "-filter_complex", filter_complex_full,
        "-map", f"[{final_video_label}]",
        "-map", "0:a?",
        "-af", audio_filter,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "160k",
        "-movflags", "+faststart",
        str(out_path),
    ]

    ffmpeg_utils.run_with_progress(
        args, total_seconds=duration, on_progress=on_progress, cancel_event=cancel_event, log_path=log_path
    )


def margin_v_for(clip: ClipConfig, out_h: int) -> int:
    if clip.stream_type == "screen_cam" and not clip.keep_full_vertical_game:
        return int(out_h * 0.08)
    return int(out_h * 0.12)


def write_ass_for_clip(clip: ClipConfig, out_w: int, out_h: int, ass_path: Path) -> None:
    blocks = [{"start": b["start"], "end": b["end"], "text": b["text"]} for b in clip.subtitles]
    content = blocks_to_ass(blocks, out_w, out_h, margin_v_for(clip, out_h))
    ass_path.write_text(content, encoding="utf-8")
