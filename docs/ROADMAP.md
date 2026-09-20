# Roadmap — xSlou Clips AI

## Fase 1 — MVP funcional (esta entrega) ✅

- [x] Crear proyecto, importar videos (archivo/carpeta/ruta).
- [x] Metadata (ffprobe), streaming con Range requests, proxy.
- [x] Transcripción (faster-whisper), silencios, picos de audio, escenas.
- [x] Clips candidatos con score y motivo, edición de inicio/fin.
- [x] Subtítulos (SRT) y exportación real 9:16 vía ffmpeg.
- [x] Cola de trabajos persistente con progreso en tiempo real (WS).

## Fase 2 — Editor visual y producción

- [ ] Editor multipista (video, facecam, subtítulos, texto, stickers, audio).
- [ ] Plantillas visuales (14 layouts) + plantillas propias.
- [ ] Detección/separación de facecam (MediaPipe) + auto-reframe.
- [ ] Subtítulos avanzados (karaoke, estilos, diccionario personalizado).
- [ ] Títulos/ganchos/hashtags sugeridos por LLM.
- [ ] Exportación por lotes + ZIP con metadata.

## Fase 3 — Especialización gaming e IA avanzada

- [ ] Plugins por videojuego (Warzone, Valorant, LoL, CS, etc.).
- [ ] Detección de kills/headshots/victorias (YOLO + OCR + audio + reglas).
- [ ] Reacciones faciales como señal adicional de score.
- [ ] Modelo entrenado sobre `UserFeedback`.
- [ ] App de escritorio (Tauri/Electron).

## Fase 4 — SaaS

- [ ] Cuentas, almacenamiento en nube, equipos, suscripciones.
- [ ] Publicación directa a redes vía APIs oficiales.
- [ ] Cola distribuida (Celery + Redis), PostgreSQL como default.
