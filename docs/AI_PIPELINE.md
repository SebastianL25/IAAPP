# Pipeline de IA — xSlou Clips AI

## Etapas (Fase 1 ✅, resto documentado)

| Etapa | Servicio | Fase | Técnica |
|---|---|---|---|
| Metadata | `ffmpeg_service.probe` | ✅ 1 | ffprobe |
| Proxy | `proxy_service` | ✅ 1 | ffmpeg h264 480p |
| Transcripción | `transcription_service` | ✅ 1 | faster-whisper |
| Silencios | `audio_analysis_service` | ✅ 1 | ffmpeg silencedetect |
| Picos de audio | `audio_analysis_service` | ✅ 1 | RMS por ventana (numpy) |
| Cambios de escena | `scene_detection_service` | ✅ 1 | ffmpeg scdet |
| Facecam / OCR / plugins de juego | — | 🔜 2-3 | MediaPipe / OCR / YOLO |
| Análisis semántico (LLM) | `semantic_service` | 🔜 (básico en 1) | proveedor configurable |
| Puntuación de viralidad | `clip_detection_service` | ✅ 1 (heurística) | fórmula ponderada |

## Proveedor de IA configurable

`AppSetting["ai_provider"]` (o `.env AI_PROVIDER`): `rule_based` (100%
local, sin LLM), `openai`, `anthropic`, `gemini`, `ollama`. Si no hay
proveedor en la nube configurado, el pipeline funciona igual solo con
señales acústicas y de escena (`RuleBasedProvider`) — nunca se sube video.

## Puntuación de viralidad (heurística, Fase 1)

```
score = 100 * clamp(
    w_audio_peak   * intensidad_pico_audio  +
    w_scene_change * cambio_de_escena       +
    w_speech       * densidad_de_habla      +
    w_no_silence   * (1 - proporcion_silencio) +
    w_semantic     * relevancia_semantica   # 0 si no hay LLM
)
```

Pesos por defecto en `clip_detection_service.DEFAULT_WEIGHTS`, editables
vía `AppSetting["score_weights"]`.

Niveles de sensibilidad (`ai_settings.sensitivity`): `conservador`
(umbral 75, separación 45s), `equilibrado` (55 / 20s, default),
`agresivo` (35 / 8s).

## Duración inteligente

Para cada ancla (pico de audio o cambio de escena), se expande la ventana
buscando el silencio/corte de escena más cercano como límite natural
(pre-roll 5-15s, post-roll 8-20s), acotado a [8s, 120s].

## Garantía de candidatos mínimos

Si las señales reales (picos + escenas) son insuficientes, se completa con
muestreo uniforme del video para garantizar al menos 5 candidatos por
video, evitando solaparse con anclas reales ya detectadas.

## Procesamiento local vs. nube

Por defecto `cloud_processing_enabled = false`: transcripción y detección
de audio/escena siempre corren localmente (ffmpeg/faster-whisper). Solo si
el usuario activa explícitamente un proveedor en la nube se envían
fragmentos de **texto transcrito** (nunca el video) a ese proveedor.
