from __future__ import annotations

import json
import re

from fastapi import APIRouter, HTTPException, UploadFile

from .. import ffmpeg_utils, storage

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi"}
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB, para no cargar el video completo en memoria


def _safe_filename(name: str) -> str:
    name = name.replace("\\", "/").split("/")[-1]
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "video"


@router.post("")
async def upload_video(file: UploadFile):
    filename = _safe_filename(file.filename or "video.mp4")
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, f"Formato no soportado ({ext}). Usa MP4, MKV, MOV, WEBM o AVI.")

    video_id = storage.new_id()
    dest_dir = storage.upload_dir(video_id)
    dest_path = dest_dir / filename

    size = 0
    with open(dest_path, "wb") as out:
        while True:
            chunk = await file.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            out.write(chunk)
    await file.close()

    try:
        probe = ffmpeg_utils.probe(dest_path)
    except Exception as exc:  # noqa: BLE001
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, f"No se pudo procesar el video: {exc}") from exc

    meta = {
        "filename": filename,
        "size": size,
        "duration": probe.duration,
        "width": probe.width,
        "height": probe.height,
        "fps": probe.fps,
        "has_audio": probe.has_audio,
    }
    (dest_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"video_id": video_id, **meta}


@router.get("/{video_id}")
def get_upload(video_id: str):
    meta_file = storage.upload_dir(video_id) / "meta.json"
    if not meta_file.exists():
        raise HTTPException(404, "Video no encontrado")
    meta = json.loads(meta_file.read_text(encoding="utf-8"))
    return {"video_id": video_id, **meta}
