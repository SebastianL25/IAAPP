from __future__ import annotations

from fastapi import APIRouter, HTTPException

from .. import analysis, audio_analysis, config, ffmpeg_utils, jobs, storage, subtitles, transcription, vision
from ..jobs import ProgressReporter
from ..models import ClipConfig

router = APIRouter(prefix="/api/projects", tags=["analyze"])


def _run_analysis(reporter: ProgressReporter, project_id: str) -> dict:
    project = storage.load_project(project_id)
    if project is None:
        raise RuntimeError("Proyecto no encontrado")

    try:
        source = storage.source_video_path(project.video_id)
        probe = ffmpeg_utils.probe(source)

        reporter.stage("Extrayendo audio")
        wav_path = storage.project_dir(project_id) / "audio.wav"
        ffmpeg_utils.extract_audio_wav(source, wav_path)
        reporter.progress(0.08)
        if reporter.cancel_event.is_set():
            raise InterruptedError()

        reporter.stage("Transcribiendo audio en español")
        segments = transcription.transcribe(
            wav_path,
            on_progress=lambda f: reporter.progress(0.08 + 0.52 * f),
            cancel_event=reporter.cancel_event,
        )

        reporter.stage("Analizando video (rostros y movimiento)")
        visual_samples = vision.analyze_video(
            source,
            on_progress=lambda f: reporter.progress(0.60 + 0.28 * f),
            cancel_event=reporter.cancel_event,
        )

        reporter.stage("Analizando intensidad de audio")
        audio_samples = audio_analysis.analyze_audio(wav_path)
        reporter.progress(0.92)

        reporter.stage("Calculando momentos destacados")
        candidates = analysis.suggest_moments(
            probe.duration,
            segments,
            audio_samples,
            visual_samples,
            project.config.clip_duration,
            project.config.clip_count,
        )

        settings = config.get_settings()
        censored_words = settings.get("censored_words", [])

        clips: list[ClipConfig] = []
        for cand in candidates:
            words = subtitles.words_in_range(segments, cand["start"], cand["end"])
            blocks = subtitles.build_subtitle_blocks(words, cand["start"], cand["end"])
            blocks, mute_intervals = subtitles.apply_censorship(blocks, words, cand["start"], censored_words)
            clips.append(
                ClipConfig(
                    id=storage.new_id(),
                    start=cand["start"],
                    end=cand["end"],
                    format=project.config.format,
                    stream_type=project.config.stream_type,
                    camera_rect=project.config.camera_rect,
                    audio_sync_ms=0,
                    subtitles_enabled=project.config.subtitles_enabled,
                    subtitles=blocks,
                    mute_intervals=[list(m) for m in mute_intervals],
                    kick_username=project.config.kick_username,
                    score=cand["score"],
                    reasons=cand["reasons"],
                )
            )

        project.clips = clips
        project.analysis_status = "done"
        storage.save_project(project)
        storage.save_analysis(
            project_id,
            {
                "segments": segments,
                "duration": probe.duration,
                "audio_samples": audio_samples[::5],
                "visual_samples": visual_samples[::2],
            },
        )
        return {"clip_count": len(clips)}
    except InterruptedError:
        project.analysis_status = "cancelled"
        storage.save_project(project)
        raise
    except Exception:
        project.analysis_status = "error"
        storage.save_project(project)
        raise


@router.post("/{project_id}/analyze")
def analyze_project(project_id: str):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    ffmpeg_path = config.resolve_ffmpeg()
    if not ffmpeg_path:
        raise HTTPException(400, "ffmpeg no está configurado. Ve a Ajustes y define su ruta.")

    project.analysis_status = "queued"
    storage.save_project(project)

    job_id = jobs.submit("analyze", project_id, lambda reporter: _run_analysis(reporter, project_id))
    project.analysis_job_id = job_id
    storage.save_project(project)
    return {"job_id": job_id}


@router.get("/{project_id}/analysis")
def get_analysis(project_id: str):
    project = storage.load_project(project_id)
    if not project:
        raise HTTPException(404, "Proyecto no encontrado")
    data = storage.load_analysis(project_id) or {}
    return {
        "status": project.analysis_status,
        "job_id": project.analysis_job_id,
        "clips": project.clips,
        "segments_preview": data.get("segments", [])[:0],
    }
