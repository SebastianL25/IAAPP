import pytest

from app.core.errors import InvalidFileError
from app.services import import_service


def test_validate_extension_accepts_supported_formats():
    for ext in ["mp4", "mov", "mkv", "avi", "webm", "ts"]:
        import_service.validate_extension(f"video.{ext}")


def test_validate_extension_rejects_unsupported_format():
    with pytest.raises(InvalidFileError):
        import_service.validate_extension("video.exe")


def test_hash_file_is_deterministic(tmp_path):
    f = tmp_path / "a.mp4"
    f.write_bytes(b"contenido de prueba")
    h1 = import_service.hash_file(f)
    h2 = import_service.hash_file(f)
    assert h1 == h2
    assert len(h1) == 64


def test_list_video_files_in_folder_filters_by_extension(tmp_path):
    (tmp_path / "clip.mp4").write_bytes(b"x")
    (tmp_path / "notes.txt").write_bytes(b"x")
    (tmp_path / "clip.mov").write_bytes(b"x")
    files = import_service.list_video_files_in_folder(tmp_path)
    names = sorted(f.name for f in files)
    assert names == ["clip.mov", "clip.mp4"]
