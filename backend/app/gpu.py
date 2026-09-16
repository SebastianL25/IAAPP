"""Detección de GPU NVIDIA disponible para acelerar la transcripción."""
from __future__ import annotations

import functools
import shutil
import subprocess


@functools.lru_cache(maxsize=1)
def cuda_available() -> bool:
    """Devuelve True si hay una GPU NVIDIA utilizable por ctranslate2/faster-whisper."""
    try:
        import ctranslate2  # type: ignore

        if ctranslate2.get_cuda_device_count() > 0:
            return True
    except Exception:
        pass

    # Alternativa: comprobar que el driver NVIDIA responde (nvidia-smi).
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "-L"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and "GPU" in result.stdout:
                return True
        except Exception:
            pass
    return False


def active_device(preferred: str = "auto") -> str:
    """Resuelve el dispositivo real a usar: 'cuda' o 'cpu'."""
    if preferred == "cpu":
        return "cpu"
    if preferred == "cuda":
        return "cuda" if cuda_available() else "cpu"
    return "cuda" if cuda_available() else "cpu"


def device_label(device: str) -> str:
    return "GPU NVIDIA (CUDA)" if device == "cuda" else "CPU"
