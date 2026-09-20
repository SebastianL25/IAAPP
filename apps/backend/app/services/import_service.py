"""Importacion de videos: subida directa, ruta local o carpeta completa.

Responsable de: validar extension/tamano, calcular hash sha256, detectar
duplicados por proyecto, copiar a storage/originals/{id}.ext, leer metadata
(ffprobe) y generar miniatura. La transcripcion/analisis pesado se hace en
el pipeline asincrono (app/workers/pipeline.py).
"""
from __future__ import annotations

import hashlib
import logging
import shutil
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import InvalidFileError, PathNotAllowedError
from app.models.video import SourceVideo, VideoMetadata
from app.services import ffmpeg_service

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".ts"}
HASH_CHUNK_SIZE = 1024 * 1024


def validate_extension(filename: str) -> None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise InvalidFileError(
            f"Extension no soportada: {ext}. Permitidas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )


def validate_path_allowed(path: Path) -> None:
    settings = get_settings()
    roots = settings.allowed_import_roots_list
    if not roots:
        return
    resolved = path.resolve()
    if not any(str(resolved).startswith(str(root)) for root in roots):
        raise PathNotAllowedError(f"La ruta {resolved} no esta dentro de ALLOWED_IMPORT_ROOTS")


def hash_file(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(HASH_CHUNK_SIZE):
            sha256.update(chunk)
    return sha256.hexdigest()


def find_duplicate(db: Session, project_id: str, file_hash: str) -> SourceVideo | None:
    return (
        db.query(SourceVideo)
        .filter(SourceVideo.project_id == project_id, SourceVideo.file_hash == file_hash)
        .first()
    )


def register_video_from_path(db: Session, project_id: str, source_path: Path, move: bool = False) -> SourceVideo:
    """Copia (o mueve) `source_path` a storage/originals, calcula hash,
    detecta duplicados, prueba metadata y genera miniatura."""
    validate_extension(source_path.name)
    validate_path_allowed(source_path)
    if not source_path.exists() or not source_path.is_file():
        raise InvalidFileError(f"El archivo no existe: {source_path}")

    settings = get_settings()
    file_hash = hash_file(source_path)

    existing = find_duplicate(db, project_id, file_hash)
    if existing:
        logger.info("Video duplicado detectado (hash=%s), reutilizando %s", file_hash[:8], existing.id)
        return existing

    video_id = str(uuid.uuid4())
    ext = source_path.suffix.lower()
    dest = settings.storage_path / "originals" / f"{video_id}{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        if move:
            shutil.move(str(source_path), str(dest))
        else:
            shutil.copy2(str(source_path), str(dest))
    except OSError as exc:
        raise InvalidFileError(f"No se pudo copiar el archivo: {exc}") from exc

    size_bytes = dest.stat().st_size

    video = SourceVideo(
        id=video_id,
        project_id=project_id,
        original_filename=source_path.name,
        storage_path=str(dest.relative_to(settings.storage_path)),
        file_hash=file_hash,
        size_bytes=size_bytes,
        import_status="importing",
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    try:
        _probe_and_thumbnail(db, video, dest)
        video.import_status = "ready"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error procesando metadata de %s", video.id)
        video.import_status = "error"
        video.error_message = str(exc)[:500]
    db.commit()
    db.refresh(video)
    return video


def _probe_and_thumbnail(db: Session, video: SourceVideo, file_path: Path) -> None:
    settings = get_settings()
    probe_data = ffmpeg_service.probe(file_path)

    metadata = VideoMetadata(
        source_video_id=video.id,
        duration_seconds=probe_data["duration_seconds"],
        width=probe_data["width"],
        height=probe_data["height"],
        fps=probe_data["fps"],
        video_codec=probe_data["video_codec"],
        audio_codec=probe_data["audio_codec"],
        bitrate=probe_data["bitrate"],
        audio_channels=probe_data["audio_channels"],
        raw_probe_json=probe_data["raw_probe_json"],
    )
    db.add(metadata)

    thumb_path = settings.storage_path / "thumbnails" / f"{video.id}.jpg"
    try:
        at = min(3.0, probe_data["duration_seconds"] / 2) if probe_data["duration_seconds"] else 0.0
        ffmpeg_service.generate_thumbnail(file_path, thumb_path, at_seconds=at)
        video.thumbnail_path = str(thumb_path.relative_to(settings.storage_path))
    except Exception:  # noqa: BLE001
        logger.warning("No se pudo generar miniatura para %s", video.id)

    db.commit()


def list_video_files_in_folder(folder: Path) -> list[Path]:
    if not folder.exists() or not folder.is_dir():
        raise InvalidFileError(f"La carpeta no existe: {folder}")
    files = [
        p
        for p in sorted(folder.rglob("*"))
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
    ]
    return files
