"""Generacion de subtitulos SRT a partir de segmentos de transcripcion.

Version Fase 1: division simple por numero maximo de palabras por linea.
Los estilos avanzados (karaoke, resaltado por palabra, temas) quedan para
Fase 2 (CaptionStyle avanzado), pero el SRT generado aqui ya puede quemarse
con ffmpeg mediante el filtro `subtitles`.
"""
from __future__ import annotations

from pathlib import Path


def _format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _chunk_words(words: list[dict], max_words: int) -> list[list[dict]]:
    return [words[i : i + max_words] for i in range(0, len(words), max_words)] or []


def build_srt_for_range(
    segments: list[dict],
    start_time: float,
    end_time: float,
    max_words_per_line: int = 6,
) -> str:
    """Genera contenido SRT solo para el rango [start_time, end_time],
    con timestamps relativos a start_time (como los espera el clip exportado)."""
    lines: list[str] = []
    index = 1

    for seg in segments:
        if seg["end_time"] <= start_time or seg["start_time"] >= end_time:
            continue

        words = seg.get("words_json") or []
        if words:
            for chunk in _chunk_words(words, max_words_per_line):
                w_start = chunk[0]["start"] - start_time
                w_end = chunk[-1]["end"] - start_time
                if w_end <= 0 or w_start >= (end_time - start_time):
                    continue
                text = " ".join(w["word"] for w in chunk)
                lines.append(str(index))
                lines.append(
                    f"{_format_timestamp(max(0.0, w_start))} --> {_format_timestamp(max(0.0, w_end))}"
                )
                lines.append(text)
                lines.append("")
                index += 1
        else:
            s = max(0.0, seg["start_time"] - start_time)
            e = seg["end_time"] - start_time
            if e <= 0:
                continue
            lines.append(str(index))
            lines.append(f"{_format_timestamp(s)} --> {_format_timestamp(e)}")
            lines.append(seg["text"])
            lines.append("")
            index += 1

    return "\n".join(lines)


def write_srt_file(content: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest
