"""Transcripcion con faster-whisper.

El modelo se carga una sola vez (singleton) y se reutiliza entre videos.
Se transcribe siempre a partir del WAV mono 16kHz extraido del proxy/original
para evitar depender de decodificadores exoticos dentro del propio whisper.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        settings = get_settings()
        logger.info(
            "Cargando modelo faster-whisper '%s' (device=%s, compute=%s)...",
            settings.whisper_model,
            settings.whisper_device,
            settings.whisper_compute_type,
        )
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
    return _model


def transcribe(
    wav_path: Path,
    language: str | None = None,
    on_progress: Callable[[float, str], None] | None = None,
) -> dict:
    """Devuelve {"language": str, "full_text": str, "segments": [...]}"""
    model = _get_model()
    settings = get_settings()
    lang = language or (settings.whisper_language or None)

    segments_iter, info = model.transcribe(
        str(wav_path),
        language=lang,
        word_timestamps=True,
        vad_filter=True,
    )

    duration = info.duration or 1.0
    segments: list[dict] = []
    full_text_parts: list[str] = []

    for seg in segments_iter:
        words = [
            {
                "word": w.word.strip(),
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "confidence": round(float(getattr(w, "probability", 1.0)), 3),
            }
            for w in (seg.words or [])
        ]
        segments.append(
            {
                "start_time": round(seg.start, 3),
                "end_time": round(seg.end, 3),
                "text": seg.text.strip(),
                "words_json": words,
            }
        )
        full_text_parts.append(seg.text.strip())
        if on_progress:
            pct = min(99.0, (seg.end / duration) * 100)
            on_progress(pct, f"Transcribiendo... {seg.end:.0f}s/{duration:.0f}s")

    return {
        "language": info.language,
        "full_text": " ".join(full_text_parts).strip(),
        "segments": segments,
    }
