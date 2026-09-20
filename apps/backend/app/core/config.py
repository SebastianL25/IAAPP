"""Configuracion global de la aplicacion, cargada desde variables de entorno.

Las rutas relativas (STORAGE_ROOT, DATABASE_URL con sqlite:///./...) se
resuelven siempre respecto a la raiz del repositorio, sin importar desde
que directorio se lance uvicorn.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# apps/backend/app/core/config.py -> repo root
REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./storage/app.db"
    storage_root: str = "./storage"
    frontend_origin: str = "http://localhost:3000"
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_language: str = ""

    ai_provider: str = "rule_based"
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    max_upload_size_mb: int = 20000
    allowed_import_roots: str = ""

    max_parallel_jobs: int = 1
    ffmpeg_threads: int = 0

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_root)
        if not p.is_absolute():
            p = (REPO_ROOT / p).resolve()
        p.mkdir(parents=True, exist_ok=True)
        for sub in ("originals", "proxies", "thumbnails", "transcripts", "exports", "temp"):
            (p / sub).mkdir(parents=True, exist_ok=True)
        return p

    @property
    def sqlalchemy_url(self) -> str:
        if self.database_url.startswith("sqlite:///./"):
            rel = self.database_url.removeprefix("sqlite:///./")
            abs_path = (REPO_ROOT / rel).resolve()
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            return f"sqlite:///{abs_path}"
        return self.database_url

    @property
    def allowed_import_roots_list(self) -> list[Path]:
        if not self.allowed_import_roots.strip():
            return []
        return [Path(p).resolve() for p in self.allowed_import_roots.split(";") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
