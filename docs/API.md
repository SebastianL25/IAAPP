# API — xSlou Clips AI (backend local, `http://localhost:8000`)

Prefijo común: `/api`. Errores: `{ "error": { "code": "...", "message": "..." } }`.

## Proyectos
| Método | Ruta | Descripción |
|---|---|---|
| POST | /api/projects | Crear proyecto |
| GET | /api/projects | Listar proyectos |
| GET | /api/projects/{id} | Detalle |
| PATCH | /api/projects/{id} | Actualizar |
| DELETE | /api/projects/{id} | Papelera (soft-delete) |

## Videos
| Método | Ruta | Descripción |
|---|---|---|
| GET | /api/videos?project_id=... | Listar videos de un proyecto |
| POST | /api/videos/import | Subir archivos (`multipart/form-data`) |
| POST | /api/videos/import-path | Importar por ruta local |
| POST | /api/videos/import-folder | Importar carpeta completa |
| GET | /api/videos/{id} | Metadata |
| GET | /api/videos/{id}/stream | Streaming con `Range` requests |
| GET | /api/videos/{id}/proxy | Streaming del proxy |
| GET | /api/videos/{id}/thumbnail | Miniatura JPEG |
| POST | /api/videos/{id}/analyze | Encola el pipeline completo |
| GET | /api/videos/{id}/analysis | Transcript + eventos + clips |
| DELETE | /api/videos/{id} | Eliminar video y derivados |

## Trabajos
| Método | Ruta | Descripción |
|---|---|---|
| GET | /api/jobs | Listar (`project_id`, `status`) |
| GET | /api/jobs/{id} | Detalle |
| POST | /api/jobs/pause-queue / resume-queue | Pausar/reanudar cola |
| POST | /api/jobs/{id}/cancel | Cancelar |
| POST | /api/jobs/{id}/retry | Reintentar |

## Clips
| Método | Ruta | Descripción |
|---|---|---|
| GET | /api/clips | Listar candidatos |
| GET | /api/clips/{id} | Detalle |
| PATCH | /api/clips/{id} | Editar inicio/fin/título |
| POST | /api/clips/{id}/approve | Aprobar + feedback |
| POST | /api/clips/{id}/discard | Descartar + feedback |
| POST | /api/clips/{id}/export | Crear ExportJob |

## Exportaciones
| Método | Ruta | Descripción |
|---|---|---|
| GET | /api/exports | Listar |
| GET | /api/exports/{id} | Estado |
| GET | /api/exports/{id}/download | Descargar MP4 |

## Transcripciones / Plantillas / Configuración
`/api/transcripts/{id}/regenerate`, `/api/transcripts/{id}/segments/{id}`,
`/api/templates`, `/api/settings`.

## WebSockets
- `WS /api/ws/jobs` — progreso global.
- `WS /api/ws/projects/{project_id}` — progreso filtrado por proyecto.

```json
{ "type": "job_progress", "job_id": "...", "status": "running",
  "progress_percent": 42.5, "stage_message": "Transcribiendo..." }
```

## Ejemplo — `ClipCandidate`

```json
{
  "id": "5b1c...", "start_time": 153.4, "end_time": 182.7,
  "viral_score": 91, "category": "gaming_highlight",
  "detected_events": ["audio_peak", "scene_change"],
  "hook": "No puede ser, los bajé a los tres",
  "reason": "Pico de intensidad de audio + cambio de escena",
  "confidence": 0.94, "status": "candidate"
}
```

## Seguridad
Ningún endpoint sirve archivos por ruta cruda (siempre por `video_id`/
`clip_id` interno). `import-path`/`import-folder` validan extensión y,
si se configura `ALLOWED_IMPORT_ROOTS`, restringen las rutas permitidas.
CORS restringido a `FRONTEND_ORIGIN`.
