"""Combina las senales de audio/escena/transcripcion en candidatos de clip
con una puntuacion de viralidad 0-100 (heuristica, Fase 1).

Ver docs/AI_PIPELINE.md seccion 5 y 6 para la formula y el razonamiento.
"""
from __future__ import annotations

SENSITIVITY_PRESETS = {
    "conservador": {"min_score": 75, "min_gap": 45},
    "equilibrado": {"min_score": 55, "min_gap": 20},
    "agresivo": {"min_score": 35, "min_gap": 8},
}

DEFAULT_WEIGHTS = {
    "audio_peak": 0.35,
    "scene_change": 0.20,
    "speech_density": 0.20,
    "no_silence": 0.15,
    "semantic": 0.10,
}

PRE_ROLL_MIN, PRE_ROLL_MAX = 5.0, 15.0
POST_ROLL_MIN, POST_ROLL_MAX = 8.0, 20.0
MIN_CLIP_DURATION, MAX_CLIP_DURATION = 8.0, 120.0


def _overlaps(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    inter = min(a_end, b_end) - max(a_start, b_start)
    if inter <= 0:
        return 0.0
    union = max(a_end, b_end) - min(a_start, b_start)
    return inter / union if union > 0 else 0.0


def _find_boundary(anchor_time: float, boundaries: list[float], direction: int, min_off: float, max_off: float) -> float:
    """Busca el limite mas cercano (silencio/cambio de escena) en la
    direccion dada, respetando offsets minimo/maximo desde el ancla."""
    candidates = [b for b in boundaries if (b - anchor_time) * direction > 0]
    if not candidates:
        return anchor_time + direction * min_off
    candidates.sort(key=lambda b: abs(b - anchor_time))
    for b in candidates:
        offset = abs(b - anchor_time)
        if min_off <= offset <= max_off:
            return b
    return anchor_time + direction * min_off


def _speech_density(segments: list[dict], start: float, end: float) -> float:
    span = max(1e-6, end - start)
    covered = 0.0
    for seg in segments:
        overlap = min(seg["end_time"], end) - max(seg["start_time"], start)
        if overlap > 0:
            covered += overlap
    return min(1.0, covered / span)


def _silence_ratio(silences: list[dict], start: float, end: float) -> float:
    span = max(1e-6, end - start)
    covered = 0.0
    for s in silences:
        overlap = min(s["end_time"], end) - max(s["start_time"], start)
        if overlap > 0:
            covered += overlap
    return min(1.0, covered / span)


def _build_hook(segments: list[dict], start: float, end: float) -> str | None:
    for seg in segments:
        if seg["start_time"] >= start and seg["start_time"] < end and seg["text"].strip():
            return seg["text"].strip()[:120]
    return None


def generate_candidates(
    duration_seconds: float,
    audio_peaks: list[dict],
    scene_changes: list[dict],
    silences: list[dict],
    transcript_segments: list[dict],
    sensitivity: str = "equilibrado",
    weights: dict | None = None,
    ensure_min_candidates: int = 5,
) -> list[dict]:
    weights = weights or DEFAULT_WEIGHTS
    preset = SENSITIVITY_PRESETS.get(sensitivity, SENSITIVITY_PRESETS["equilibrado"])
    scene_times = [e["metadata_json"].get("cut_at", e["start_time"]) for e in scene_changes]
    boundary_times = sorted(
        scene_times + [s["start_time"] for s in silences] + [s["end_time"] for s in silences]
    )

    anchors: list[dict] = []
    for peak in audio_peaks:
        anchors.append({"time": (peak["start_time"] + peak["end_time"]) / 2, "kind": "audio_peak", "conf": peak.get("confidence", 0.6)})
    for scene in scene_changes:
        anchors.append({"time": scene["metadata_json"].get("cut_at", scene["start_time"]), "kind": "scene_change", "conf": scene.get("confidence", 0.5)})

    if len(anchors) < ensure_min_candidates:
        # Senales insuficientes: completar con muestreo uniforme para
        # garantizar al menos `ensure_min_candidates` candidatos, evitando
        # quedar demasiado cerca de un ancla real ya detectada.
        step = max(20.0, duration_seconds / max(1, ensure_min_candidates))
        t = step / 2
        existing_times = [a["time"] for a in anchors]
        while t < duration_seconds and len(anchors) < ensure_min_candidates:
            if all(abs(t - e) >= step / 2 for e in existing_times):
                anchors.append({"time": t, "kind": "sampled", "conf": 0.3})
                existing_times.append(t)
            t += step

    anchors.sort(key=lambda a: a["time"])

    raw_candidates: list[dict] = []
    for anchor in anchors:
        t = anchor["time"]
        start = _find_boundary(t, boundary_times, -1, PRE_ROLL_MIN, PRE_ROLL_MAX)
        end = _find_boundary(t, boundary_times, 1, POST_ROLL_MIN, POST_ROLL_MAX)
        start = max(0.0, start)
        end = min(duration_seconds, end)
        if end - start < MIN_CLIP_DURATION:
            end = min(duration_seconds, start + MIN_CLIP_DURATION)
        if end - start > MAX_CLIP_DURATION:
            end = start + MAX_CLIP_DURATION

        audio_peak_score = 1.0 if anchor["kind"] == "audio_peak" else 0.3
        scene_score = 1.0 if anchor["kind"] == "scene_change" else 0.3
        speech_density = _speech_density(transcript_segments, start, end)
        no_silence = 1.0 - _silence_ratio(silences, start, end)
        semantic_score = 0.0  # RuleBasedProvider por defecto en Fase 1

        score01 = (
            weights["audio_peak"] * audio_peak_score
            + weights["scene_change"] * scene_score
            + weights["speech_density"] * speech_density
            + weights["no_silence"] * no_silence
            + weights["semantic"] * semantic_score
        )
        score = int(round(max(0.0, min(1.0, score01)) * 100))

        events_detected = [anchor["kind"]]
        if speech_density > 0.4:
            events_detected.append("speech")
        if no_silence > 0.8:
            events_detected.append("sustained_energy")

        reason_parts = []
        if anchor["kind"] == "audio_peak":
            reason_parts.append("pico de intensidad de audio")
        if anchor["kind"] == "scene_change":
            reason_parts.append("cambio de escena")
        if anchor["kind"] == "sampled":
            reason_parts.append("muestreo uniforme (sin picos fuertes detectados)")
        if speech_density > 0.4:
            reason_parts.append("habla continua")
        if no_silence > 0.8:
            reason_parts.append("sin silencios prolongados")

        raw_candidates.append(
            {
                "start_time": round(start, 2),
                "end_time": round(end, 2),
                "viral_score": score,
                "category": "gaming_highlight" if anchor["kind"] != "sampled" else "general",
                "detected_events": events_detected,
                "hook": _build_hook(transcript_segments, start, end),
                "reason": ", ".join(reason_parts).capitalize() or "Momento detectado automaticamente",
                "confidence": round(anchor["conf"], 2),
            }
        )

    raw_candidates.sort(key=lambda c: c["viral_score"], reverse=True)

    selected: list[dict] = []
    for cand in raw_candidates:
        if any(
            _overlaps(cand["start_time"], cand["end_time"], s["start_time"], s["end_time"]) > 0.5
            for s in selected
        ):
            continue
        if selected and cand["viral_score"] < preset["min_score"]:
            if len(selected) >= ensure_min_candidates:
                continue
        too_close = any(abs(cand["start_time"] - s["start_time"]) < preset["min_gap"] for s in selected)
        if too_close and cand["viral_score"] < preset["min_score"]:
            continue
        selected.append(cand)

    if len(selected) < ensure_min_candidates:
        for cand in raw_candidates:
            if len(selected) >= ensure_min_candidates:
                break
            if cand in selected:
                continue
            if any(_overlaps(cand["start_time"], cand["end_time"], s["start_time"], s["end_time"]) > 0.5 for s in selected):
                continue
            selected.append(cand)

    selected.sort(key=lambda c: c["start_time"])
    return selected
