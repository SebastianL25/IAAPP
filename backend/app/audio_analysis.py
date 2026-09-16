"""Cálculo de intensidad de audio (RMS por ventana) a partir de un WAV mono 16kHz."""
from __future__ import annotations

import wave
from pathlib import Path
from typing import TypedDict

import numpy as np


class AudioSample(TypedDict):
    t: float
    rms: float  # 0..1 normalizado


def analyze_audio(wav_path: Path, window_seconds: float = 1.0) -> list[AudioSample]:
    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        framerate = wf.getframerate()
        n_frames = wf.getnframes()
        raw = wf.readframes(n_frames)

    if sample_width != 2:
        # Nos aseguramos de extraer siempre PCM 16-bit en ffmpeg_utils.extract_audio_wav
        raise RuntimeError("Formato de audio inesperado (se esperaba PCM 16-bit).")

    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32)
    if n_channels > 1:
        data = data.reshape(-1, n_channels).mean(axis=1)

    window_samples = max(1, int(window_seconds * framerate))
    samples: list[AudioSample] = []
    max_rms = 1e-6
    raw_values: list[float] = []
    for start in range(0, len(data), window_samples):
        chunk = data[start : start + window_samples]
        if len(chunk) == 0:
            continue
        rms = float(np.sqrt(np.mean(np.square(chunk))))
        raw_values.append(rms)
        max_rms = max(max_rms, rms)
        t = start / framerate
        samples.append({"t": t, "rms": rms})

    for s in samples:
        s["rms"] = round(s["rms"] / max_rms, 4)

    return samples
