from app.services import caption_service


def test_build_srt_for_range_produces_relative_timestamps():
    segments = [
        {"start_time": 10.0, "end_time": 12.0, "text": "Hola a todos", "words_json": []},
        {"start_time": 20.0, "end_time": 22.0, "text": "fuera de rango", "words_json": []},
    ]
    srt = caption_service.build_srt_for_range(segments, start_time=8.0, end_time=15.0)
    assert "Hola a todos" in srt
    assert "fuera de rango" not in srt
    assert "00:00:02,000 --> 00:00:04,000" in srt


def test_build_srt_uses_word_level_chunks_when_available():
    words = [{"word": w, "start": 10.0 + i * 0.3, "end": 10.3 + i * 0.3, "confidence": 0.9} for i, w in enumerate(
        ["no", "puede", "ser", "los", "baje", "a", "los", "tres"]
    )]
    segments = [{"start_time": 10.0, "end_time": 12.5, "text": "no puede ser...", "words_json": words}]
    srt = caption_service.build_srt_for_range(segments, start_time=10.0, end_time=12.5, max_words_per_line=3)
    assert "no puede ser" in srt
    assert "los baje a" in srt


def test_write_srt_file_creates_parent_dirs(tmp_path):
    dest = tmp_path / "nested" / "clip.srt"
    caption_service.write_srt_file("1\n00:00:00,000 --> 00:00:01,000\nhola\n", dest)
    assert dest.exists()
    assert "hola" in dest.read_text(encoding="utf-8")
