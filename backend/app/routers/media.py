"""Sirve los videos subidos con soporte real de HTTP Range para permitir
buscar (scrub) en videos largos sin cargarlos completos en memoria ni descargarlos enteros."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from .. import config

router = APIRouter(prefix="/media/uploads", tags=["media"])

CHUNK_SIZE = 1024 * 1024  # 1MB por lectura


def _guess_content_type(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".mov": "video/quicktime",
        ".webm": "video/webm",
        ".avi": "video/x-msvideo",
    }.get(ext, "application/octet-stream")


@router.get("/{video_id}/{filename}")
def stream_video(video_id: str, filename: str, request: Request):
    safe_video_id = re.sub(r"[^a-fA-F0-9]", "", video_id)
    path = config.UPLOADS_DIR / safe_video_id / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Archivo no encontrado")

    file_size = path.stat().st_size
    range_header = request.headers.get("range")
    content_type = _guess_content_type(path)

    if range_header:
        m = re.match(r"bytes=(\d*)-(\d*)", range_header)
        if not m:
            raise HTTPException(416, "Rango inválido")
        start_s, end_s = m.groups()
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start >= file_size:
            raise HTTPException(416, "Rango fuera de límites")
        length = end - start + 1

        def iterator():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk

        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
        }
        return StreamingResponse(iterator(), status_code=206, media_type=content_type, headers=headers)

    def full_iterator():
        with open(path, "rb") as f:
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                yield chunk

    headers = {"Accept-Ranges": "bytes", "Content-Length": str(file_size)}
    return StreamingResponse(full_iterator(), media_type=content_type, headers=headers)
