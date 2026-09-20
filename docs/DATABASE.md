# Modelo de datos — xSlou Clips AI

SQLite en desarrollo (`storage/app.db`), PostgreSQL en producción vía
`DATABASE_URL`. Migraciones con Alembic (`apps/backend/alembic/`).
Los archivos de video **nunca** se guardan en la base de datos: solo rutas
relativas a `storage/`, hashes y metadata.

Implementadas en **Fase 1** (marcadas ✅) y modeladas pero no usadas hasta
fases posteriores (marcadas 🔜).

## Entidades

### User 🔜
Preparada para Fase 4 (SaaS). En Fase 1 se usa un usuario local implícito
(`is_local=True`, sin autenticación).

### CreatorProfile ✅
| campo | tipo |
|---|---|
| id | UUID PK |
| display_name | str (ej. "xSlou") |
| content_types | JSON |
| logo_path | str, nullable |
| brand_colors / fonts / social_links | JSON |
| watermark_path | str, nullable |
| default_facecam_position | str, nullable |
| preferred_duration | int, nullable |
| preferred_platforms | JSON |

### Project ✅
| campo | tipo |
|---|---|
| id | UUID PK |
| name | str |
| game_or_category | str, nullable |
| target_platform | str |
| language | str, default "es" |
| ai_settings | JSON (sensibilidad, proveedor LLM, etc.) |
| status | enum(active, archived, trashed) |
| created_at / updated_at | datetime |

### SourceVideo ✅
| campo | tipo |
|---|---|
| id | UUID PK |
| project_id | FK Project |
| original_filename / storage_path | str |
| proxy_path / thumbnail_path | str, nullable |
| file_hash | str (sha256, único por proyecto) |
| size_bytes | int |
| import_status | enum(pending, importing, ready, error, duplicate) |

### VideoMetadata ✅ (1:1 con SourceVideo)
duration_seconds, width, height, fps, video_codec, audio_codec, bitrate,
audio_channels, raw_probe_json.

### Transcript ✅ / TranscriptSegment ✅
Transcripción completa + segmentos con `words_json` (timestamps por
palabra, para subtítulos karaoke).

### DetectedEvent ✅
event_type (silence, audio_peak, scene_change...), start_time, end_time,
confidence, metadata_json, source (audio/video/semantic).

### ClipCandidate ✅
start_time, end_time, viral_score (0-100), category, detected_events,
hook, reason, confidence, status (candidate/approved/discarded).

### ClipVersion ✅ / Timeline ✅ / TimelineTrack 🔜 / TimelineItem 🔜
Una versión editada de un candidato (recorte + formato). Timeline se crea
vacía en Fase 1; se completa con el editor multipista en Fase 2.

### Template 🔜 / CaptionStyle ✅ (mínimo)
Plantillas visuales y estilos de subtítulos.

### ExportJob ✅ / ProcessingJob ✅
Colas de exportación y de análisis, con progreso y estado persistente.

### AIProvider ✅ / UserFeedback ✅ / GamePlugin 🔜 / AppSetting ✅
Configuración de proveedor de IA, feedback de aprobación/descarte para
recalibrar el scoring, plugins de juego (Fase 3), configuración global.

## Migraciones

```bash
cd apps/backend
alembic revision --autogenerate -m "mensaje"
alembic upgrade head
```
