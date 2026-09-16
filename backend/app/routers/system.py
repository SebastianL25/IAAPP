from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from .. import config, ffmpeg_utils, gpu, transcription

router = APIRouter(prefix="/api/system", tags=["system"])


class SettingsPatch(BaseModel):
    ffmpeg_path: str | None = None
    ffprobe_path: str | None = None
    whisper_model: str | None = None
    whisper_device: str | None = None
    compute_type: str | None = None
    censored_words: list[str] | None = None


@router.get("/status")
def status():
    settings = config.get_settings()
    ffmpeg_path = config.resolve_ffmpeg()
    ffprobe_path = config.resolve_ffprobe()
    device = gpu.active_device(settings.get("whisper_device", "auto"))
    return {
        "ffmpeg_ok": bool(ffmpeg_path),
        "ffmpeg_path": ffmpeg_path,
        "ffprobe_ok": bool(ffprobe_path),
        "ffprobe_path": ffprobe_path,
        "gpu": {
            "cuda_available": gpu.cuda_available(),
            "active_device": device,
            "label": gpu.device_label(device),
        },
        "whisper_model": settings.get("whisper_model"),
        "model_likely_downloaded": transcription.model_ready(settings.get("whisper_model", "medium")),
    }


@router.get("/settings")
def get_settings():
    return config.get_settings()


@router.put("/settings")
def update_settings(patch: SettingsPatch):
    return config.update_settings(patch.model_dump(exclude_unset=True))


@router.post("/check-ffmpeg")
def check_ffmpeg():
    path = config.resolve_ffmpeg()
    if not path:
        return {"ok": False, "message": "ffmpeg no encontrado en PATH ni en la ruta configurada."}
    try:
        import subprocess

        result = subprocess.run([path, "-version"], capture_output=True, text=True, timeout=10)
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        return {"ok": result.returncode == 0, "message": first_line, "path": path}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "message": str(exc)}
