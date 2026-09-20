"""Analisis de audio: silencios y picos de energia (RMS por ventana).

Los silencios se detectan con ffmpeg silencedetect (ver ffmpeg_service).
Los picos se calculan leyendo el WAV mono de 16kHz ya generado para la
transcripcion, sin dependencias pesadas adicionales (solo `wave` + numpy).
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from app.services import ffmpeg_service


def detect_silences(source: Path) -> list[dict]:
    return ffmpeg_service.detect_silences(source)


def detect_audio_peaks(wav_path: Path, window_seconds: float = 1.0, z_threshold: float = 1.6) -> list[dict]:
    """Divide el audio en ventanas y marca aquellas cuya energia RMS supera
    `media + z_threshold * desviacion_estandar`."""
    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if n_frames == 0:
        return []

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if n_channels > 1:
        samples = samples.reshape(-1, n_channels).mean(axis=1)

    window_size = max(1, int(window_seconds * sample_rate))
    n_windows = len(samples) // window_size
    if n_windows == 0:
        return []

    trimmed = samples[: n_windows * window_size].reshape(n_windows, window_size)
    rms = np.sqrt(np.mean(trimmed ** 2, axis=1) + 1e-9)

    mean_rms = float(np.mean(rms))
    std_rms = float(np.std(rms)) or 1.0

    peaks: list[dict] = []
    for i, value in enumerate(rms):
        z = (value - mean_rms) / std_rms
        if z >= z_threshold and value > 0:
            start = i * window_seconds
            peaks.append(
                {
                    "start_time": round(start, 3),
                    "end_time": round(start + window_seconds, 3),
                    "confidence": float(min(1.0, max(0.0, z / (z_threshold * 2)))),
                    "metadata_json": {"rms": float(value), "z_score": float(z)},
                }
            )

    return _merge_adjacent(peaks)


def _merge_adjacent(events: list[dict], gap: float = 0.5) -> list[dict]:
    if not events:
        return []
    events = sorted(events, key=lambda e: e["start_time"])
    merged = [events[0]]
    for ev in events[1:]:
        last = merged[-1]
        if ev["start_time"] - last["end_time"] <= gap:
            last["end_time"] = max(last["end_time"], ev["end_time"])
            last["confidence"] = max(last["confidence"], ev["confidence"])
        else:
            merged.append(ev)
    return merged


def speech_density(segments_times: list[tuple[float, float]], window_start: float, window_end: float) -> float:
    """Proporcion del rango [window_start, window_end] cubierta por habla."""
    span = max(1e-6, window_end - window_start)
    covered = 0.0
    for s, e in segments_times:
        overlap = min(e, window_end) - max(s, window_start)
        if overlap > 0:
            covered += overlap
    return min(1.0, covered / span)
