"""Generación de subtítulos (bloques cortos, formato .ass) y censura de palabras."""
from __future__ import annotations

import unicodedata
from typing import TypedDict

from .transcription import Segment, Word


class SubtitleBlock(TypedDict):
    start: float  # tiempo local del clip (segundos)
    end: float
    text: str


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in normalized if not unicodedata.combining(c))
    return stripped.lower().strip(".,;:!?¡¿\"'()")


def words_in_range(segments: list[Segment], start: float, end: float) -> list[Word]:
    words: list[Word] = []
    for seg in segments:
        for w in seg.get("words", []):
            if w["end"] > start and w["start"] < end:
                words.append(w)
    words.sort(key=lambda w: w["start"])
    return words


def build_subtitle_blocks(
    words: list[Word],
    clip_start: float,
    clip_end: float,
    max_words: int = 4,
    max_block_seconds: float = 2.5,
    pause_gap: float = 0.6,
) -> list[SubtitleBlock]:
    blocks: list[SubtitleBlock] = []
    current: list[Word] = []

    def flush():
        if not current:
            return
        start = max(0.0, current[0]["start"] - clip_start)
        end = min(clip_end - clip_start, current[-1]["end"] - clip_start)
        text = " ".join(w["text"] for w in current).strip()
        if text:
            blocks.append({"start": start, "end": max(end, start + 0.2), "text": text})
        current.clear()

    prev_end: float | None = None
    for w in words:
        if w["start"] < clip_start or w["end"] > clip_end:
            # recortar parcialmente la palabra en el borde del clip
            w = {"start": max(w["start"], clip_start), "end": min(w["end"], clip_end), "text": w["text"]}
        if prev_end is not None and (w["start"] - prev_end) > pause_gap and current:
            flush()
        current.append(w)
        block_span = current[-1]["end"] - current[0]["start"]
        if len(current) >= max_words or block_span >= max_block_seconds:
            flush()
        prev_end = w["end"]
    flush()
    return blocks


def apply_censorship(
    blocks: list[SubtitleBlock],
    words: list[Word],
    clip_start: float,
    censored_words: list[str],
) -> tuple[list[SubtitleBlock], list[tuple[float, float]]]:
    """Enmascara palabras censuradas en el texto y devuelve intervalos (locales) a silenciar."""
    censored_norm = {_normalize(w) for w in censored_words if w.strip()}
    if not censored_norm:
        return blocks, []

    mute_intervals: list[tuple[float, float]] = []
    for w in words:
        if _normalize(w["text"]) in censored_norm:
            mute_intervals.append((w["start"] - clip_start, w["end"] - clip_start))

    new_blocks: list[SubtitleBlock] = []
    for block in blocks:
        tokens = block["text"].split(" ")
        masked_tokens = []
        for tok in tokens:
            if _normalize(tok) in censored_norm:
                clean = "".join(c for c in tok if c.isalnum())
                masked_tokens.append("*" * max(3, len(clean)))
            else:
                masked_tokens.append(tok)
        new_blocks.append({**block, "text": " ".join(masked_tokens)})

    return new_blocks, mute_intervals


def _ass_time(t: float) -> str:
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    cs = int(round((t - int(t)) * 100))
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def blocks_to_ass(blocks: list[SubtitleBlock], video_w: int, video_h: int, margin_v: int) -> str:
    font_size = max(28, int(video_h * 0.045))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,60,60,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = []
    for b in blocks:
        text = b["text"].replace("\n", " ").replace("{", "(").replace("}", ")")
        lines.append(
            f"Dialogue: 0,{_ass_time(b['start'])},{_ass_time(b['end'])},Default,,0,0,0,,{text}"
        )
    return header + "\n".join(lines) + "\n"
