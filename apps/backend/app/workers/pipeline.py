"""Pipeline de analisis (Fase 1), ejecutado en un hilo por job_queue.

Etapas: proxy -> extraccion de audio -> transcripcion -> silencios/picos ->
cambios de escena -> deteccion de clips candidatos. Cada etapa reporta
progreso via `job_queue.update_progress`, que a su vez difunde por
WebSocket. El estado final queda en SQLite (ProcessingJob, DetectedEvent,
Transcript, ClipCandidate), por lo que sobrevive a reinicios.
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import get_settings
from app.database.session import SessionLocal
from app.models.clip import ClipCandidate
from app.models.job import ExportJob, ProcessingJob
from app.models.video import DetectedEvent, SourceVideo, Transcript, TranscriptSegment
from app.services import (
    audio_analysis_service,
    clip_detection_service,
    export_service,
    ffmpeg_service,
    proxy_service,
    scene_detection_service,
    transcription_service,
)
from app.workers import job_queue

logger = logging.getLogger(__name__)


class JobCancelled(Exception):
    pass


def _check_cancelled(job_id: str) -> None:
    if job_queue.is_cancelled(job_id):
        raise JobCancelled()


def run_job(job_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        job: ProcessingJob | None = db.get(ProcessingJob, job_id)
        if not job:
            logger.warning("Job %s no encontrado", job_id)
            return

        video: SourceVideo | None = db.get(SourceVideo, job.source_video_id)
        if not video:
            job_queue.mark_error(job_id, "Video fuente no encontrado")
            return

        job_queue.update_progress(job_id, 1, "Iniciando analisis...", status="running")
        source_path = settings.storage_path / video.storage_path

        # --- Etapa 1: proxy ---
        _check_cancelled(job_id)
        job_queue.update_progress(job_id, 5, "Generando proxy de baja resolucion...")
        proxy_path = proxy_service.ensure_proxy(video.id, source_path)
        video.proxy_path = str(proxy_path.relative_to(settings.storage_path))
        db.commit()

        # --- Etapa 2: extraccion de audio ---
        _check_cancelled(job_id)
        job_queue.update_progress(job_id, 20, "Extrayendo audio...")
        wav_path = settings.storage_path / "temp" / f"{video.id}.wav"
        ffmpeg_service.extract_audio_wav(proxy_path, wav_path)

        # --- Etapa 3: transcripcion ---
        _check_cancelled(job_id)
        job_queue.update_progress(job_id, 30, "Transcribiendo audio...")

        transcript = db.query(Transcript).filter(Transcript.source_video_id == video.id).first()
        if not transcript:
            transcript = Transcript(source_video_id=video.id, status="running", model_size=settings.whisper_model)
            db.add(transcript)
            db.commit()
            db.refresh(transcript)

        def on_progress(pct: float, message: str) -> None:
            overall = 30 + (pct / 100) * 40  # 30% - 70%
            job_queue.update_progress(job_id, overall, message)

        result = transcription_service.transcribe(wav_path, on_progress=on_progress)

        transcript.language = result["language"]
        transcript.full_text = result["full_text"]
        transcript.status = "done"
        db.query(TranscriptSegment).filter(TranscriptSegment.transcript_id == transcript.id).delete()
        segment_rows = []
        for seg in result["segments"]:
            row = TranscriptSegment(
                transcript_id=transcript.id,
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"],
                words_json=seg["words_json"],
            )
            db.add(row)
            segment_rows.append(seg)
        db.commit()

        # --- Etapa 4: silencios y picos de audio ---
        _check_cancelled(job_id)
        job_queue.update_progress(job_id, 72, "Detectando silencios y picos de audio...")
        db.query(DetectedEvent).filter(
            DetectedEvent.source_video_id == video.id,
            DetectedEvent.event_type.in_(["silence", "audio_peak", "scene_change"]),
        ).delete(synchronize_session=False)

        silences = audio_analysis_service.detect_silences(proxy_path)
        for s in silences:
            db.add(
                DetectedEvent(
                    source_video_id=video.id,
                    event_type="silence",
                    start_time=s["start_time"],
                    end_time=s["end_time"],
                    confidence=1.0,
                    source="audio",
                )
            )

        peaks = audio_analysis_service.detect_audio_peaks(wav_path)
        for p in peaks:
            db.add(
                DetectedEvent(
                    source_video_id=video.id,
                    event_type="audio_peak",
                    start_time=p["start_time"],
                    end_time=p["end_time"],
                    confidence=p["confidence"],
                    metadata_json=p["metadata_json"],
                    source="audio",
                )
            )
        db.commit()

        # --- Etapa 5: cambios de escena ---
        _check_cancelled(job_id)
        job_queue.update_progress(job_id, 82, "Detectando cambios de escena...")
        scene_threshold = 0.35
        project = video.project
        if project and project.ai_settings:
            scene_threshold = project.ai_settings.get("scene_threshold", 0.35)
        scenes = scene_detection_service.detect_scene_changes(proxy_path, threshold=scene_threshold)
        for sc in scenes:
            db.add(
                DetectedEvent(
                    source_video_id=video.id,
                    event_type="scene_change",
                    start_time=sc["start_time"],
                    end_time=sc["end_time"],
                    confidence=sc["confidence"],
                    metadata_json=sc["metadata_json"],
                    source="video",
                )
            )
        db.commit()

        # --- Etapa 6: deteccion de clips candidatos ---
        _check_cancelled(job_id)
        job_queue.update_progress(job_id, 90, "Generando clips candidatos...")

        video_meta = video.video_metadata
        duration = video_meta.duration_seconds if video_meta else 0.0
        sensitivity = "equilibrado"
        if project and project.ai_settings:
            sensitivity = project.ai_settings.get("sensitivity", "equilibrado")

        db.query(ClipCandidate).filter(ClipCandidate.source_video_id == video.id).delete(
            synchronize_session=False
        )

        candidates = clip_detection_service.generate_candidates(
            duration_seconds=duration,
            audio_peaks=peaks,
            scene_changes=scenes,
            silences=silences,
            transcript_segments=segment_rows,
            sensitivity=sensitivity,
        )
        for cand in candidates:
            db.add(
                ClipCandidate(
                    project_id=video.project_id,
                    source_video_id=video.id,
                    start_time=cand["start_time"],
                    end_time=cand["end_time"],
                    viral_score=cand["viral_score"],
                    category=cand["category"],
                    detected_events=cand["detected_events"],
                    hook=cand["hook"],
                    reason=cand["reason"],
                    confidence=cand["confidence"],
                    status="candidate",
                )
            )
        db.commit()

        wav_path.unlink(missing_ok=True)
        job_queue.update_progress(job_id, 100, f"Analisis completo: {len(candidates)} clips detectados", status="done")

    except JobCancelled:
        job_queue.update_progress(job_id, 0, "Cancelado por el usuario", status="cancelled")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error en pipeline de analisis para job %s", job_id)
        job_queue.mark_error(job_id, str(exc))
    finally:
        db.close()


def run_export_job(export_job_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        job: ExportJob | None = db.get(ExportJob, export_job_id)
        if not job:
            return
        job_queue.update_export_progress(export_job_id, 5, status="running")

        clip_version = job.clip_version
        clip_candidate = clip_version.clip_candidate
        video = db.get(SourceVideo, clip_candidate.source_video_id)
        project = video.project

        source_path = settings.storage_path / video.storage_path

        transcript = db.query(Transcript).filter(Transcript.source_video_id == video.id).first()
        segments = []
        if transcript:
            segments = [
                {"start_time": s.start_time, "end_time": s.end_time, "text": s.text, "words_json": s.words_json}
                for s in transcript.segments
            ]

        job_queue.update_export_progress(export_job_id, 20)

        existing_exports = (
            db.query(ExportJob)
            .join(ExportJob.clip_version)
            .filter(ExportJob.id != export_job_id)
            .count()
        )
        filename = export_service.build_output_filename(
            project.name if project else "proyecto",
            clip_index=existing_exports + 1,
            viral_score=clip_candidate.viral_score,
        )
        output_path = settings.storage_path / "exports" / filename

        export_service.export_clip(
            source_video_path=source_path,
            output_path=output_path,
            start_time=clip_version.start_time,
            end_time=clip_version.end_time,
            aspect_ratio=clip_version.aspect_ratio,
            fps=job.fps,
            burn_captions=True,
            transcript_segments=segments,
            resolution_override=job.resolution,
        )

        job.output_path = str(output_path.relative_to(settings.storage_path))
        db.commit()
        job_queue.update_export_progress(export_job_id, 100, status="done")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Error exportando clip %s", export_job_id)
        job_queue.mark_export_error(export_job_id, str(exc))
    finally:
        db.close()
