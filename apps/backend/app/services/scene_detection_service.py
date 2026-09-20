from __future__ import annotations

from pathlib import Path

from app.services import ffmpeg_service


def detect_scene_changes(proxy_or_source: Path, threshold: float = 0.35) -> list[dict]:
    timestamps = ffmpeg_service.detect_scene_changes(proxy_or_source, threshold=threshold)
    events = []
    for t in timestamps:
        events.append(
            {
                "start_time": round(max(0.0, t - 0.25), 3),
                "end_time": round(t + 0.25, 3),
                "confidence": 0.8,
                "metadata_json": {"cut_at": t},
            }
        )
    return events
