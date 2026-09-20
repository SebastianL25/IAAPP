from app.services import clip_detection_service as svc


def test_generates_minimum_candidates_with_no_signals():
    """Con un video largo pero sin picos/escenas detectados, el sistema
    debe seguir generando candidatos via muestreo uniforme."""
    candidates = svc.generate_candidates(
        duration_seconds=600.0,
        audio_peaks=[],
        scene_changes=[],
        silences=[],
        transcript_segments=[],
        sensitivity="equilibrado",
        ensure_min_candidates=5,
    )
    assert len(candidates) >= 5
    for c in candidates:
        assert c["end_time"] > c["start_time"]
        assert 0 <= c["viral_score"] <= 100


def test_audio_peak_produces_higher_score_than_uniform_sample():
    candidates = svc.generate_candidates(
        duration_seconds=120.0,
        audio_peaks=[{"start_time": 50.0, "end_time": 52.0, "confidence": 0.9}],
        scene_changes=[],
        silences=[],
        transcript_segments=[{"start_time": 50.0, "end_time": 55.0, "text": "wow"}],
        sensitivity="equilibrado",
        ensure_min_candidates=3,
    )
    peak_candidates = [c for c in candidates if "audio_peak" in c["detected_events"]]
    sampled_candidates = [c for c in candidates if "sampled" in c["detected_events"]]
    assert peak_candidates, "debe existir al menos un candidato anclado en el pico de audio"
    if sampled_candidates:
        assert max(c["viral_score"] for c in peak_candidates) > min(c["viral_score"] for c in sampled_candidates)


def test_no_overlapping_candidates_returned():
    candidates = svc.generate_candidates(
        duration_seconds=300.0,
        audio_peaks=[
            {"start_time": 30.0, "end_time": 31.0, "confidence": 0.8},
            {"start_time": 31.5, "end_time": 32.5, "confidence": 0.75},
        ],
        scene_changes=[],
        silences=[],
        transcript_segments=[],
        sensitivity="agresivo",
    )
    for i, a in enumerate(candidates):
        for b in candidates[i + 1 :]:
            overlap = min(a["end_time"], b["end_time"]) - max(a["start_time"], b["start_time"])
            union = max(a["end_time"], b["end_time"]) - min(a["start_time"], b["start_time"])
            assert (overlap / union if union > 0 else 0) <= 0.5


def test_sensitivity_presets_exist():
    for level in ("conservador", "equilibrado", "agresivo"):
        assert level in svc.SENSITIVITY_PRESETS
