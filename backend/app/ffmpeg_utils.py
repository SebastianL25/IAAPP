"""Envoltura de ffmpeg/ffprobe: sondeo, corte, filtros de encuadre, subtítulos y progreso real."""
from __future__ import annotations

import json
import re
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from . import config


class FFmpegNotFoundError(RuntimeError):
    pass


@dataclass
class ProbeResult:
    duration: float
    width: int
    height: int
    fps: float
    has_audio: bool


def probe(path: Path) -> ProbeResult:
    ffprobe = config.resolve_ffprobe()
    if not ffprobe:
        raise FFmpegNotFoundError("No se encontró ffprobe. Configura la ruta en Ajustes.")
    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe falló: {out.stderr.strip()}")
    data = json.loads(out.stdout)
    video_stream = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    if video_stream is None:
        raise RuntimeError("El archivo no contiene una pista de video válida.")
    duration = float(data.get("format", {}).get("duration") or video_stream.get("duration") or 0.0)
    width = int(video_stream.get("width") or 0)
    height = int(video_stream.get("height") or 0)
    fps_raw = video_stream.get("avg_frame_rate") or "25/1"
    try:
        num, den = fps_raw.split("/")
        fps = float(num) / float(den) if float(den) != 0 else float(num)
    except Exception:
        fps = 25.0
    return ProbeResult(duration=duration, width=width, height=height, fps=fps, has_audio=audio_stream is not None)


def _ffmpeg_bin() -> str:
    ffmpeg = config.resolve_ffmpeg()
    if not ffmpeg:
        raise FFmpegNotFoundError(
            "No se encontró ffmpeg. Descárgalo e indica su ruta absoluta en Ajustes."
        )
    return ffmpeg


class Cancelled(Exception):
    pass


def run_with_progress(
    args: list[str],
    total_seconds: float,
    on_progress: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
    log_path: Optional[Path] = None,
) -> None:
    """Ejecuta ffmpeg con -progress pipe:1 y reporta avance real 0..1."""
    ffmpeg = _ffmpeg_bin()
    full_cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", *args, "-progress", "pipe:1", "-nostats"]
    log_file = open(log_path, "a", encoding="utf-8") if log_path else None
    try:
        proc = subprocess.Popen(
            full_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        stderr_lines: list[str] = []

        def _read_stderr():
            assert proc.stderr is not None
            for line in proc.stderr:
                stderr_lines.append(line)
                if log_file:
                    log_file.write(line)

        t = threading.Thread(target=_read_stderr, daemon=True)
        t.start()

        assert proc.stdout is not None
        for line in proc.stdout:
            if cancel_event is not None and cancel_event.is_set():
                proc.terminate()
                raise Cancelled("Trabajo cancelado por el usuario")
            m = re.match(r"out_time_ms=(\d+)", line.strip())
            if m and on_progress and total_seconds > 0:
                out_ms = int(m.group(1))
                frac = min(1.0, (out_ms / 1_000_000) / total_seconds)
                on_progress(frac)
        proc.wait()
        t.join(timeout=2)
        if proc.returncode != 0 and proc.returncode is not None and not (cancel_event and cancel_event.is_set()):
            raise RuntimeError("ffmpeg error: " + "".join(stderr_lines[-40:]))
    finally:
        if log_file:
            log_file.close()


def extract_audio_wav(src: Path, dst: Path) -> None:
    ffmpeg = _ffmpeg_bin()
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(src),
        "-vn", "-ac", "1", "-ar", "16000", "-f", "wav",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"No se pudo extraer el audio: {result.stderr.strip()}")


FORMAT_RESOLUTIONS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}


def build_sync_filter(offset_ms: int) -> str:
    """Devuelve el filtro de audio para desfasar +/-2000ms."""
    if offset_ms == 0:
        return "anull"
    if offset_ms > 0:
        return f"adelay={offset_ms}|{offset_ms}"
    trim_s = abs(offset_ms) / 1000.0
    return f"atrim=start={trim_s:.3f},asetpts=PTS-STARTPTS"


def build_mute_filter(mute_intervals: list[tuple[float, float]]) -> str:
    """Filtro de audio que silencia (volumen 0) los intervalos [start,end] dados (en segundos, tiempo local del clip)."""
    if not mute_intervals:
        return "anull"
    parts = [f"between(t,{max(0.0, s):.3f},{max(0.0, e):.3f})" for s, e in mute_intervals]
    expr = "+".join(parts)
    return f"volume=0:enable='gte({expr},1)'"
