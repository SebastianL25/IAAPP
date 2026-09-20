"""Wrapper seguro sobre ffmpeg/ffprobe.

Todos los argumentos se pasan como listas (nunca se construye un string de
shell con entrada del usuario), evitando inyeccion de comandos.
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

from app.core.errors import FFmpegError

logger = logging.getLogger(__name__)

FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"
FFPROBE_BIN = shutil.which("ffprobe") or "ffprobe"


def check_ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def probe(path: Path) -> dict[str, Any]:
    """Ejecuta ffprobe y devuelve metadata estructurada + json crudo."""
    cmd = [
        FFPROBE_BIN,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise FFmpegError(f"ffprobe fallo para {path.name}: {result.stderr[:500]}")

    raw = json.loads(result.stdout)
    video_stream = next((s for s in raw.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in raw.get("streams", []) if s.get("codec_type") == "audio"), None)
    fmt = raw.get("format", {})

    fps = 0.0
    if video_stream and video_stream.get("avg_frame_rate"):
        num, _, den = video_stream["avg_frame_rate"].partition("/")
        try:
            fps = float(num) / float(den) if float(den or 0) != 0 else float(num)
        except (ValueError, ZeroDivisionError):
            fps = 0.0

    return {
        "duration_seconds": float(fmt.get("duration", 0) or 0),
        "width": int(video_stream.get("width", 0)) if video_stream else 0,
        "height": int(video_stream.get("height", 0)) if video_stream else 0,
        "fps": round(fps, 3),
        "video_codec": video_stream.get("codec_name") if video_stream else None,
        "audio_codec": audio_stream.get("codec_name") if audio_stream else None,
        "bitrate": int(fmt.get("bit_rate", 0) or 0),
        "audio_channels": int(audio_stream.get("channels", 0)) if audio_stream else 0,
        "raw_probe_json": raw,
    }


def is_valid_media_file(path: Path) -> bool:
    try:
        data = probe(path)
        return data["duration_seconds"] > 0 and (data["width"] > 0 or data["audio_codec"])
    except Exception:
        return False


def generate_thumbnail(source: Path, dest: Path, at_seconds: float = 3.0) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", str(max(0.0, at_seconds)),
        "-i", str(source),
        "-frames:v", "1",
        "-vf", "scale=480:-2",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0 or not dest.exists():
        raise FFmpegError(f"No se pudo generar la miniatura: {result.stderr[:500]}")


def generate_proxy(source: Path, dest: Path, height: int = 480) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", str(source),
        "-vf", f"scale=-2:{height}",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "30",
        "-g", "30",
        "-c:a", "aac",
        "-b:a", "96k",
        "-movflags", "+faststart",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0 or not dest.exists():
        raise FFmpegError(f"No se pudo generar el proxy: {result.stderr[:800]}")


def extract_audio_wav(source: Path, dest: Path, sample_rate: int = 16000) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        FFMPEG_BIN, "-y",
        "-i", str(source),
        "-vn",
        "-ac", "1",
        "-ar", str(sample_rate),
        "-f", "wav",
        str(dest),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if result.returncode != 0 or not dest.exists():
        raise FFmpegError(f"No se pudo extraer el audio: {result.stderr[:500]}")


def detect_silences(source: Path, noise_db: float = -35.0, min_duration: float = 0.7) -> list[dict]:
    cmd = [
        FFMPEG_BIN,
        "-i", str(source),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_duration}",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    silences: list[dict] = []
    start = None
    for line in result.stderr.splitlines():
        if "silence_start" in line:
            try:
                start = float(line.split("silence_start:")[1].strip().split(" ")[0])
            except (IndexError, ValueError):
                start = None
        elif "silence_end" in line and start is not None:
            try:
                part = line.split("silence_end:")[1].strip()
                end = float(part.split(" ")[0])
                silences.append({"start_time": start, "end_time": end})
            except (IndexError, ValueError):
                pass
            start = None
    return silences


def detect_scene_changes(source: Path, threshold: float = 0.35) -> list[float]:
    cmd = [
        FFMPEG_BIN,
        "-i", str(source),
        "-filter:v", f"select='gt(scene,{threshold})',showinfo",
        "-f", "null", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    timestamps: list[float] = []
    for line in result.stderr.splitlines():
        if "pts_time:" not in line:
            continue
        try:
            token = line.split("pts_time:")[1].split(" ")[0]
            timestamps.append(float(token))
        except (IndexError, ValueError):
            continue
    return timestamps


def cut_and_reframe(
    source: Path,
    dest: Path,
    start_time: float,
    end_time: float,
    target_width: int,
    target_height: int,
    subtitles_path: Path | None = None,
    fps: int | None = None,
    crf: int = 20,
) -> None:
    """Recorta [start,end], reencuadra a target_width x target_height (crop
    centrado + scale) y opcionalmente quema subtitulos SRT."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    duration = max(0.1, end_time - start_time)

    vf_parts = [
        f"scale=-2:{target_height}:force_original_aspect_ratio=increase",
        f"crop={target_width}:{target_height}",
    ]
    if subtitles_path is not None:
        escaped = str(subtitles_path).replace("\\", "/").replace(":", "\\:")
        vf_parts.append(f"subtitles='{escaped}'")
    vf = ",".join(vf_parts)

    cmd = [
        FFMPEG_BIN, "-y",
        "-ss", str(start_time),
        "-i", str(source),
        "-t", str(duration),
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", str(crf),
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
    ]
    if fps:
        cmd += ["-r", str(fps)]
    cmd.append(str(dest))

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0 or not dest.exists():
        raise FFmpegError(f"No se pudo exportar el clip: {result.stderr[:1000]}")
