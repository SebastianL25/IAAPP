# Arquitectura — xSlou Clips AI

## 1. Visión general

xSlou Clips AI es una aplicación **local-first** para streamers que convierte
VODs largos en clips verticales listos para TikTok/Reels/Shorts. El
procesamiento pesado (ffmpeg, transcripción, análisis) corre en un backend
local (`http://localhost:8000`) controlado desde un frontend web
(`http://localhost:3000`). No se sube ningún archivo a servidores externos;
solo el texto transcrito puede enviarse opcionalmente a un LLM externo si el
usuario configura un proveedor en la nube (ver `AI_PIPELINE.md`).

La arquitectura está preparada para dos evoluciones futuras sin romper el
diseño actual:

- **Escritorio (Fase 3)**: empaquetar el mismo frontend + backend con
  Tauri/Electron, reemplazando "carpeta vigilada por el usuario" por acceso
  nativo al sistema de archivos.
- **SaaS (Fase 4)**: el backend ya separa `AppSetting`/`AIProvider` de la
  lógica de negocio y usa IDs opacos para servir archivos, lo que permite
  migrar de SQLite→PostgreSQL y de disco local→object storage cambiando solo
  la capa de `storage_backend` sin tocar servicios ni API.

## 2. Diagrama de componentes

```
┌─────────────────────────────┐        HTTP/WS         ┌───────────────────────────────┐
│   Frontend (Vite + React)   │◄───────────────────────►│   Backend (FastAPI, Uvicorn)   │
│   localhost:3000            │                          │   localhost:8000               │
│                              │                          │                                 │
│  - Importer                  │   GET  /api/media/*     │  api/         (routers)         │
│  - Library / Projects        │   POST /api/videos/...  │  services/    (lógica ffmpeg/IA)│
│  - Processing Queue (WS)     │   WS   /api/ws/jobs      │  workers/     (cola de trabajos)│
│  - Clip Review               │                          │  websocket/   (progreso)        │
│  - Editor (canvas)           │                          │  database/    (SQLAlchemy)      │
└─────────────────────────────┘                          └───────────────┬────────────────┘
                                                                          │
                                                    ┌─────────────────────┼─────────────────────┐
                                                    │                     │                     │
                                              ┌─────▼─────┐       ┌──────▼──────┐       ┌───────▼───────┐
                                              │  SQLite    │       │   FFmpeg /   │       │  IA (local o  │
                                              │ (metadata) │       │   FFprobe    │       │  proveedor    │
                                              │            │       │  (subprocess)│       │  configurable)│
                                              └────────────┘       └──────────────┘       └───────────────┘
                                                                          │
                                                                  ┌───────▼────────┐
                                                                  │  storage/       │
                                                                  │  originals/     │
                                                                  │  proxies/       │
                                                                  │  thumbnails/    │
                                                                  │  transcripts/   │
                                                                  │  exports/       │
                                                                  └─────────────────┘
```

## 3. Por qué esta arquitectura

- **FastAPI + SQLite en Fase 1**: cero infraestructura externa para correr
  `pip install -r requirements.txt && uvicorn app.main:app`. SQLAlchemy usa
  `DATABASE_URL` desde `.env`, por lo que cambiar a PostgreSQL en producción
  es solo una variable de entorno + `alembic upgrade head`.
- **Cola de trabajos propia (sin Redis/Celery) en Fase 1**: un
  `JobQueue` en memoria + tabla `processing_job` en SQLite. Cada paso del
  pipeline actualiza su fila en la base de datos, de modo que si el proceso
  se reinicia, el estado de los trabajos (`pending`, `running`, `done`,
  `error`) sobrevive y puede reanudarse. Se documenta en `ROADMAP.md` la
  migración a Celery/Redis para Fase 4 (multi-worker, multi-usuario).
- **Streaming de video vía endpoint con `Range` requests**: el navegador
  nunca recibe una ruta de archivo del sistema, solo un `video_id` (UUID)
  que el backend resuelve internamente. Esto evita path traversal y permite
  seek instantáneo.
- **Proxies de baja resolución**: todo clip candidato y el editor trabajan
  sobre un proxy (480p, CRF alto, keyframes cada segundo) generado una vez
  al importar. La exportación final vuelve a leer el archivo original en
  máxima calidad.
- **Pipeline de IA por etapas y desacoplado del proveedor**: cada servicio
  (`transcription_service`, `audio_analysis_service`, etc.) expone una
  interfaz simple (input: paths + metadata, output: filas de BD). El LLM de
  clasificación semántica se selecciona mediante `AppSetting.ai_provider`
  (`openai`, `anthropic`, `gemini`, `ollama`), ver `AI_PIPELINE.md`.
- **Arquitectura de plugins por juego (Fase 3)**: `GamePlugin` es una tabla +
  interfaz Python (`app/services/game_plugins/base.py`) que registra
  detectores específicos (kill, headshot, victory screen). En Fase 1 no se
  implementan detectores de juego; la interfaz queda preparada pero vacía.

## 4. Flujo end-to-end (Fase 1)

1. El usuario crea un `Project` en el frontend.
2. Importa uno o varios videos (selector de archivos, carpeta o drag&drop).
   El frontend sube los archivos al backend (`POST /api/videos/import`,
   `multipart/form-data`) o, si ya están en disco accesible por el backend,
   se referencia la ruta directamente.
3. `import_service` calcula el hash SHA-256, copia/mueve el archivo a
   `storage/originals/{video_id}.ext`, y crea `SourceVideo` +
   `VideoMetadata` (vía `ffmpeg_service.probe`).
4. Se genera una miniatura (`ffmpeg_service.thumbnail`) y se encola un
   `ProcessingJob` de tipo `analyze`.
5. El `JobQueue` ejecuta, en un hilo/proceso worker, el pipeline:
   `proxy → transcribe → audio_analysis → scene_detection → clip_detection`.
   Cada paso emite progreso por WebSocket (`/api/ws/jobs`).
6. `clip_detection_service` combina las señales de las etapas anteriores en
   una lista de `ClipCandidate` con `viral_score`, `category`, `reason`.
7. El frontend muestra los candidatos en "Clip Review"; el usuario ajusta
   inicio/fin en el editor básico, elige formato 9:16 y pulsa "Exportar".
8. `export_service` invoca ffmpeg (crop/scale/burn de subtítulos) y genera
   el archivo final en `storage/exports/`.

## 5. Riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| faster-whisper/torch son pesados y lentos en CPU | Usar modelo `small`/`base` por defecto, configurable; documentar tiempos esperados en SETUP.md |
| Path traversal al servir archivos | Servir siempre por `video_id`/`clip_id` (UUID), nunca por ruta cruda; validar extensión y resolver rutas dentro de `storage/` |
| Procesos ffmpeg colgados o llenando disco | Timeouts en subprocess, limpieza de `storage/temp`, límite de tamaño configurable |
| Falta de GPU en la mayoría de PCs de streamers | CPU como fallback obligatorio en todos los servicios; NVENC/QSV/AMF son *opcionales* y se detectan en runtime |
| Bloqueo del hilo principal de FastAPI por tareas largas | Pipeline corre en `ThreadPoolExecutor`/subprocess, nunca en el request handler async |
| Estado de cola perdido al cerrar el navegador | Todo el estado vive en SQLite (`processing_job`), no en memoria del frontend |
| Colisión entre puertos 3000/8000 ya en uso | Configurable vía `.env` (`BACKEND_PORT`, `FRONTEND_PORT`) |

## 6. Convenciones

- IDs primarios: UUID v4 en string.
- Timestamps en UTC, ISO 8601.
- Toda ruta de archivo se guarda relativa a `storage/` en la base de datos.
- Los servicios no lanzan excepciones genéricas: usan excepciones tipadas en
  `app/core/errors.py` que la capa API traduce a HTTP.
