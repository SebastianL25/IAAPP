# xSlou Clips AI

Aplicacion local para streamers (gaming, Warzone, Valorant, terror, Just
Chatting) que importa VODs largos, los analiza con IA y genera clips
verticales listos para TikTok, Instagram Reels, YouTube Shorts y Facebook
Reels — inspirada en el flujo de herramientas como Opus Clip/Eklipse, pero
con codigo, disenio y marca 100% originales.

Corre localmente: frontend en `http://localhost:3000`, backend en
`http://localhost:8000`. El procesamiento pesado (ffmpeg, transcripcion)
ocurre en tu propia maquina; nada se sube a servidores externos por defecto.

## Estado del proyecto

Esta entrega implementa **Fase 1 (MVP funcional)**. Ver `docs/ROADMAP.md`
para el plan completo por fases y `docs/ARCHITECTURE.md` para las
decisiones de diseno.

Funciona hoy:

- Crear proyectos y organizar videos/clips por proyecto.
- Importar videos (drag & drop, selector de archivos, carpeta completa, o
  ruta local) con deteccion de duplicados por hash y validacion de formato.
- Lectura de metadata (ffprobe), miniaturas y proxy de baja resolucion.
- Reproduccion del video original o del proxy via streaming HTTP con
  soporte de `Range requests` (seek instantaneo).
- Pipeline de analisis automatico: transcripcion (faster-whisper),
  deteccion de silencios, picos de audio y cambios de escena.
- Generacion automatica de clips candidatos con puntuacion de viralidad
  (0-100), categoria, motivo y eventos detectados.
- Edicion basica de inicio/fin de cada clip, aprobar/descartar con feedback.
- Exportacion real a MP4 vertical (9:16, tambien 16:9/1:1/4:5) con
  subtitulos quemados, usando ffmpeg.
- Cola de trabajos con progreso en tiempo real por WebSocket, persistente
  en SQLite (sobrevive a reinicios del backend).

## Documentacion

| Documento | Contenido |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Arquitectura, diagrama de componentes, riesgos y decisiones tecnicas |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Plan de fases 1-4 |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Modelo de datos y entidades |
| [`docs/API.md`](docs/API.md) | Referencia de endpoints REST y WebSocket |
| [`docs/AI_PIPELINE.md`](docs/AI_PIPELINE.md) | Pipeline de IA, proveedores configurables, formula de viralidad |
| [`docs/SETUP.md`](docs/SETUP.md) | Instalacion paso a paso (incluye Windows) |

## Inicio rapido

Requisitos: Python 3.11+, Node.js 18+, FFmpeg/FFprobe en el PATH. Ver
`docs/SETUP.md` para instrucciones detalladas (incluye Windows).

```bash
# 1. Configura variables de entorno
cp .env.example .env

# 2. Backend
cd apps/backend
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# 3. Frontend (en otra terminal)
cd apps/frontend
npm install
npm run dev
```

Abre `http://localhost:3000`, crea un proyecto e importa tus primeros
videos.

## Estructura del repositorio

```
xslou-clips-ai/
├── apps/
│   ├── backend/     # FastAPI + SQLAlchemy + servicios de IA/ffmpeg
│   └── frontend/    # React + Vite + TypeScript + Tailwind
├── storage/         # originals/ proxies/ thumbnails/ transcripts/ exports/ temp/
├── docs/            # Documentacion de arquitectura, API, roadmap...
└── .env.example
```

## Pruebas

```bash
cd apps/backend && source .venv/bin/activate && pytest
cd apps/frontend && npm run typecheck
```

## Licencia y marcas

Proyecto original ("xSlou Clips AI" es un nombre provisional). No incluye
codigo, assets ni identidad visual de terceros.
