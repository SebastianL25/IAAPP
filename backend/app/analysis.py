"""Combina transcripción, audio y video para proponer momentos destacados.

Esto es un heurístico, no una medición objetiva de "viralidad". Cada sugerencia
incluye el desglose de los factores que la generaron para que el usuario decida.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import TypedDict

from .transcription import Segment

HIGHLIGHT_KEYWORDS = [
    "increible", "no puede ser", "no lo puedo creer", "wow", "uau", "vamos",
    "ganamos", "perdimos", "cuidado", "imposible", "dios mio", "wtf",
    "otra vez", "que locura", "que fuerte", "no manches", "jajaja", "jaja",
    "por favor", "nooo", "siii", "genial", "brutal", "épico", "epico",
]

WEIGHTS = {"keyword": 0.30, "audio": 0.30, "motion": 0.20, "face": 0.20}


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def _normalize(text: str) -> str:
    return _strip_accents(text.lower()).strip()


class Candidate(TypedDict):
    start: float
    end: float
    score: float
    reasons: list[str]
    transcript_preview: str


@dataclass
class Timeline:
    duration: float
    resolution: float = 1.0
    values: list[float] = field(default_factory=list)
    keyword_at: dict[int, list[str]] = field(default_factory=dict)

    def bucket_count(self) -> int:
        return max(1, int(self.duration / self.resolution) + 1)


def _keyword_hits(segments: list[Segment]) -> dict[int, list[str]]:
    hits: dict[int, list[str]] = {}
    for seg in segments:
        norm_text = _normalize(seg["text"])
        for kw in HIGHLIGHT_KEYWORDS:
            if kw in norm_text:
                bucket = int(seg["start"])
                hits.setdefault(bucket, []).append(kw)
    return hits


def build_score_timeline(
    duration: float,
    segments: list[Segment],
    audio_samples: list[dict],
    visual_samples: list[dict],
    resolution: float = 1.0,
) -> Timeline:
    n = max(1, int(duration / resolution) + 1)
    kw_hits = _keyword_hits(segments)

    audio_arr = [0.0] * n
    for s in audio_samples:
        idx = int(s["t"] / resolution)
        if 0 <= idx < n:
            audio_arr[idx] = max(audio_arr[idx], s["rms"])

    motion_arr = [0.0] * n
    face_arr = [0.0] * n
    for s in visual_samples:
        idx = int(s["t"] / resolution)
        if 0 <= idx < n:
            motion_arr[idx] = max(motion_arr[idx], s["motion"])
            face_arr[idx] = 1.0 if s["face_count"] > 0 else face_arr[idx]

    kw_arr = [0.0] * n
    for bucket in kw_hits:
        idx = int(bucket / resolution)
        if 0 <= idx < n:
            kw_arr[idx] = 1.0

    values = [
        WEIGHTS["keyword"] * kw_arr[i]
        + WEIGHTS["audio"] * audio_arr[i]
        + WEIGHTS["motion"] * motion_arr[i]
        + WEIGHTS["face"] * face_arr[i]
        for i in range(n)
    ]
    return Timeline(duration=duration, resolution=resolution, values=values, keyword_at=kw_hits)


def _smooth(values: list[float], window: int) -> list[float]:
    if window <= 1:
        return values[:]
    n = len(values)
    out = [0.0] * n
    for i in range(n):
        lo = max(0, i - window // 2)
        hi = min(n, i + window // 2 + 1)
        out[i] = sum(values[lo:hi]) / (hi - lo)
    return out


def _snap_to_sentence(target: float, segments: list[Segment], is_start: bool, tolerance: float) -> float:
    best = target
    best_dist = tolerance
    for seg in segments:
        bound = seg["start"] if is_start else seg["end"]
        dist = abs(bound - target)
        if dist < best_dist:
            best = bound
            best_dist = dist
    return best


def _transcript_between(segments: list[Segment], start: float, end: float) -> str:
    parts = [seg["text"] for seg in segments if seg["start"] < end and seg["end"] > start]
    return " ".join(parts).strip()


def _reasons_for_window(timeline: Timeline, start: float, end: float) -> list[str]:
    reasons: list[str] = []
    lo = int(start / timeline.resolution)
    hi = int(end / timeline.resolution)
    kws = set()
    for b in range(lo, hi + 1):
        kws.update(timeline.keyword_at.get(b, []))
    if kws:
        reasons.append("Frases destacadas: " + ", ".join(sorted(kws)[:5]))
    if any(timeline.values[i] for i in range(lo, min(hi + 1, len(timeline.values)))):
        pass
    return reasons or ["Aumento combinado de energía de audio y actividad visual"]


def suggest_moments(
    duration: float,
    segments: list[Segment],
    audio_samples: list[dict],
    visual_samples: list[dict],
    clip_duration: float,
    count: int,
) -> list[Candidate]:
    if duration <= 0:
        return []
    clip_duration = max(3.0, min(clip_duration, duration))
    timeline = build_score_timeline(duration, segments, audio_samples, visual_samples)
    smooth_window = max(3, int(clip_duration / (3 * timeline.resolution)))
    smoothed = _smooth(timeline.values, smooth_window)

    if not smoothed:
        return []
    mean = sum(smoothed) / len(smoothed)
    variance = sum((v - mean) ** 2 for v in smoothed) / len(smoothed)
    std = variance ** 0.5

    order = sorted(range(len(smoothed)), key=lambda i: smoothed[i], reverse=True)

    min_gap = clip_duration * 0.5
    selected: list[tuple[float, float, float]] = []  # start, end, score

    def overlaps_or_close(s: float, e: float) -> bool:
        for os_, oe_, _ in selected:
            if s < oe_ + min_gap and e > os_ - min_gap:
                return True
        return False

    for idx in order:
        if len(selected) >= count:
            break
        center = idx * timeline.resolution
        raw_start = max(0.0, center - clip_duration / 2)
        raw_end = min(duration, raw_start + clip_duration)
        raw_start = max(0.0, raw_end - clip_duration)

        tolerance = clip_duration * 0.25
        start = _snap_to_sentence(raw_start, segments, is_start=True, tolerance=tolerance)
        end = _snap_to_sentence(raw_end, segments, is_start=False, tolerance=tolerance)
        if end - start < clip_duration * 0.5:
            end = min(duration, start + clip_duration)
        if end <= start:
            continue
        if overlaps_or_close(start, end):
            continue
        score = smoothed[idx]
        selected.append((start, end, score))

    selected.sort(key=lambda x: x[0])

    if not selected:
        return []

    max_score = max(s for _, _, s in selected) or 1e-6
    candidates: list[Candidate] = []
    for start, end, score in selected:
        normalized_score = round(min(99.0, (score / max_score) * 60 + 30), 1) if max_score > 0 else 50.0
        candidates.append(
            {
                "start": round(start, 2),
                "end": round(end, 2),
                "score": normalized_score,
                "reasons": _reasons_for_window(timeline, start, end),
                "transcript_preview": _transcript_between(segments, start, end)[:280],
            }
        )
    return candidates
