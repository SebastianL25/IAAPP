"""Transcripción en español con faster-whisper, con timestamps por palabra."""
from __future__ import annotations

import functools
import threading
from pathlib import Path
from typing import Callable, Optional, TypedDict

from . import config, gpu


class Word(TypedDict):
    start: float
    end: float
    text: str


class Segment(TypedDict):
    start: float
    end: float
    text: str
    words: list[Word]


_model_lock = threading.Lock()
_loaded_model = None
_loaded_key: tuple[str, str, str] | None = None


def _get_model():
    global _loaded_model, _loaded_key
    settings = config.get_settings()
    model_size = settings.get("whisper_model", "medium")
    device_pref = settings.get("whisper_device", "auto")
    device = gpu.active_device(device_pref)
    compute_type = settings.get("compute_type", "auto")
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    key = (model_size, device, compute_type)
    with _model_lock:
        if _loaded_model is not None and _loaded_key == key:
            return _loaded_model, device
        from faster_whisper import WhisperModel

        _loaded_model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(config.MODELS_DIR),
        )
        _loaded_key = key
        return _loaded_model, device


def transcribe(
    audio_path: Path,
    on_progress: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> list[Segment]:
    """Transcribe un WAV completo en español, devolviendo segmentos con palabras con timestamp."""
    model, device = _get_model()
    segments_iter, info = model.transcribe(
        str(audio_path),
        language="es",
        word_timestamps=True,
        vad_filter=True,
        beam_size=5,
    )
    total_duration = info.duration or 1.0
    results: list[Segment] = []
    for seg in segments_iter:
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Transcripción cancelada")
        words: list[Word] = []
        if seg.words:
            for w in seg.words:
                words.append({"start": float(w.start), "end": float(w.end), "text": w.word.strip()})
        results.append(
            {
                "start": float(seg.start),
                "end": float(seg.end),
                "text": seg.text.strip(),
                "words": words,
            }
        )
        if on_progress:
            on_progress(min(1.0, float(seg.end) / total_duration))
    return results


def model_ready(model_size: str) -> bool:
    """Comprueba heurísticamente si el modelo ya está descargado (evita nueva descarga silenciosa)."""
    marker = config.MODELS_DIR / f"models--Systran--faster-whisper-{model_size}"
    return marker.exists()
