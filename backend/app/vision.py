"""Detección de rostros y actividad visual (movimiento) con OpenCV, muestreando frames."""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Callable, Optional, TypedDict

import cv2
import numpy as np


class VisualSample(TypedDict):
    t: float
    face_count: int
    motion: float  # 0..1 normalizado


_face_cascade: cv2.CascadeClassifier | None = None


def _cascade() -> cv2.CascadeClassifier:
    global _face_cascade
    if _face_cascade is None:
        path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        _face_cascade = cv2.CascadeClassifier(path)
    return _face_cascade


def analyze_video(
    path: Path,
    sample_fps: float = 2.0,
    on_progress: Optional[Callable[[float], None]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> list[VisualSample]:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("No se pudo abrir el video para el análisis visual.")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    frame_step = max(1, int(round(src_fps / sample_fps)))

    cascade = _cascade()
    samples: list[VisualSample] = []
    prev_gray = None
    frame_idx = 0
    motions_raw: list[float] = []

    while True:
        if cancel_event is not None and cancel_event.is_set():
            raise InterruptedError("Análisis visual cancelado")
        ok = cap.grab()
        if not ok:
            break
        if frame_idx % frame_step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            small = cv2.resize(frame, (320, int(320 * frame.shape[0] / frame.shape[1])))
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

            faces = cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(30, 30))

            motion = 0.0
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(prev_gray, gray)
                motion = float(np.mean(diff))
            prev_gray = gray

            t = frame_idx / src_fps
            samples.append({"t": t, "face_count": int(len(faces)), "motion": motion})
            motions_raw.append(motion)

            if on_progress and total_frames > 0:
                on_progress(min(1.0, frame_idx / total_frames))
        frame_idx += 1

    cap.release()

    if motions_raw:
        max_motion = max(motions_raw) or 1.0
        for s in samples:
            s["motion"] = round(s["motion"] / max_motion, 4)

    return samples
