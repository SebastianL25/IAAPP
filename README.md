# xSlou Clips AI

Aplicación web local para Windows que convierte streams largos en clips verticales
(TikTok, Instagram Reels, YouTube Shorts). Todo el procesamiento de video, audio y
transcripción se ejecuta **en tu computador**: no se sube ningún video ni transcripción
a servicios externos.

## Requisitos (una sola vez)

1. **Windows 10/11**.
2. **Python 3.10 o superior** — https://www.python.org/downloads/ (marca "Add Python to PATH").
3. **Node.js LTS** — https://nodejs.org/ (se usa solo para compilar la interfaz, no en tiempo de ejecución).
4. **FFmpeg** para Windows — por ejemplo la build de https://www.gyan.dev/ffmpeg/builds/
   (descarga "release full", descomprime en cualquier carpeta, por ejemplo `C:\ffmpeg`).
   No es necesario añadirlo al PATH: puedes indicar la ruta absoluta de `ffmpeg.exe`
   directamente dentro de la app (menú **Ajustes**). Si ya tienes ffmpeg en el PATH,
   la app lo detecta automáticamente.
5. (Opcional, recomendado si tienes una GPU NVIDIA) Drivers NVIDIA actualizados.
   La app detecta automáticamente si hay una GPU CUDA disponible y la usa para acelerar
   la transcripción; si no la encuentra, usa la CPU. Siempre se muestra en pantalla cuál
   está activa.

No se necesitan permisos de administrador en ningún paso: todo se instala dentro de la
carpeta del proyecto.

## Instalación

1. Descomprime este proyecto en una carpeta, por ejemplo `C:\xSlouClipsAI`.
2. Haz doble clic en **`Instalar.bat`**. Esto crea un entorno de Python aislado, instala
   sus dependencias y compila la interfaz web. Puede tardar varios minutos la primera vez
   (descarga paquetes de Python y de Node).
3. Cuando termine, haz doble clic en **`Iniciar.bat`**. Se abrirá tu navegador en
   `http://127.0.0.1:8756` con la aplicación.

### Primera vez usando la IA de transcripción

La primera vez que pulses "Analizar stream con IA", `faster-whisper` descargará el
modelo de reconocimiento de voz en español (una sola vez, requiere conexión a internet
solo para esa descarga; se guarda en `backend/data/models` para reutilizarse siempre
sin conexión). El tamaño del modelo se puede cambiar en **Ajustes** (de `tiny`, más
rápido, a `large-v3`, más preciso).

## Flujo de uso

1. Sube tu video (MP4, MKV, MOV, WEBM o AVI).
2. Configura formato, duración y cantidad de clips, tipo de stream, posición de la
   cámara, usuario de Kick y subtítulos.
3. Pulsa "Analizar stream con IA": la app extrae el audio, transcribe en español con
   timestamps por palabra, detecta rostros y movimiento con OpenCV, y combina todo para
   sugerir los momentos más relevantes (con puntuación y explicación, **no** una promesa
   de viralidad).
4. Revisa cada clip sugerido: ajusta inicio/fin, encuadre de cámara y de contenido
   (arrastrando los recuadros sobre el video), formato, sincronización de audio,
   subtítulos y palabras censuradas.
5. Exporta cada clip individualmente o usa "Exportar todos" + "Descargar ZIP".

Los trabajos de análisis y exportación corren en segundo plano con progreso real y se
pueden cancelar. Si recargas la página, el proyecto y sus clips se recuperan
automáticamente (quedan guardados en `backend/data/`).

## Arquitectura

```
backend/   FastAPI + ffmpeg + faster-whisper + OpenCV (procesamiento real, local)
frontend/  React + TypeScript + Vite (interfaz oscura con acentos verde lima)
```

- `backend/app/ffmpeg_utils.py` — sondeo, corte y ejecución de ffmpeg con progreso real.
- `backend/app/transcription.py` — faster-whisper en español con timestamps por palabra,
  selecciona GPU (CUDA) o CPU automáticamente.
- `backend/app/vision.py` — detección de rostros (Haar Cascade) y actividad/movimiento
  con OpenCV, muestreando frames (no decodifica el video completo en memoria).
- `backend/app/audio_analysis.py` — intensidad de audio (RMS) por ventana de tiempo.
- `backend/app/analysis.py` — combina todo lo anterior en una puntuación por segundo,
  detecta picos, ajusta los cortes a límites de frase y evita clips repetidos o
  demasiado cercanos.
- `backend/app/subtitles.py` — agrupa palabras en bloques cortos, aplica la lista de
  palabras censuradas (asteriscos + silencio puntual) y genera `.ass` para incrustar.
- `backend/app/export.py` — construye el filtro de ffmpeg según el modo (pantalla+cámara
  apilado, solo cámara, o juego vertical completo con fondo difuminado), añade
  subtítulos, marca de agua `KICK.COM/USUARIO` y sincronización de audio.
- `backend/app/jobs.py` — trabajos en segundo plano con progreso, ETA y cancelación.
- `backend/app/routers/media.py` — sirve los videos subidos con soporte real de HTTP
  Range, para poder buscar (scrub) en videos de más de una hora sin cargarlos enteros.

## Estado de las funciones (qué es real y qué queda pendiente)

Todo lo descrito arriba está implementado con procesamiento real (no hay botones
simulados ni resultados inventados): subida por streaming a disco, sondeo con ffprobe,
extracción de audio, transcripción con faster-whisper, detección de rostros/movimiento
con OpenCV, heurística de momentos destacados, edición de encuadre por arrastre,
subtítulos editables con censura real (audio silenciado + texto con asteriscos),
exportación H.264/AAC con los tres modos de encuadre, marca de agua, sincronización de
audio, cola de exportación, descarga individual y ZIP, y persistencia en disco para
recuperar el proyecto tras recargar la página.

Quedan pendientes (no implementadas, indicado explícitamente para no prometer algo que
no existe):

- **Recuperación de trabajos tras reiniciar el backend**: si cierras y vuelves a abrir
  la app mientras un trabajo estaba corriendo, ese trabajo en concreto no se retoma
  automáticamente (sí se recupera el proyecto y los clips ya generados). Recargar la
  página mientras el backend sigue abierto sí funciona correctamente.
- **Modo "en vivo" conectado a Kick**: ver la sección siguiente.
- El arrastre de recuadros de encuadre no fuerza que la proporción coincida exactamente
  con el formato de salida (ffmpeg ajusta el resto con recorte); es un compromiso
  deliberado para mantener el arrastre simple, pero puede requerir pequeños ajustes.
- No se ha podido probar en una máquina Windows real dentro de este entorno de
  desarrollo (se probó de punta a punta en Linux con ffmpeg, OpenCV y el pipeline de
  exportación funcionando correctamente); revisa el flujo completo con tu propio video
  de prueba tras instalar.

## Sobre la API de Kick y un futuro "modo en vivo"

Investigué esto porque lo preguntaste explícitamente: Kick tiene una **API pública
oficial** (OAuth2, en `docs.kick.com`) con eventos de canal, chat, seguidores y estado
de "en vivo". **No existe un endpoint para extraer video o clips del stream en vivo**
(no hay un "Clips API" como en Twitch). Por lo tanto, conectar esta app a "sacar clips
mientras haces stream" no puede hacerse pidiéndole el video a la API de Kick.

La vía técnicamente viable —y que no requiere ningún permiso especial de Kick, porque
usa la reproducción pública de tu propio canal— sería: capturar tú mismo la señal HLS
pública de tu stream (con `ffmpeg` o `streamlink`) mientras transmites, mantener un
buffer local rodante, y aplicarle este mismo motor de análisis (audio + video, y
opcionalmente eventos de chat de la API de Kick para detectar picos de hype) para
proponer y cortar clips casi en tiempo real. **Esto no está implementado en esta
entrega**; quedaría como una fase 2 que reutiliza todo el motor ya construido
(`ffmpeg_utils`, `analysis`, `subtitles`, `export`).

## Solución de problemas

- **"FFmpeg no encontrado"**: abre Ajustes y escribe la ruta completa a `ffmpeg.exe`
  (por ejemplo `C:\ffmpeg\bin\ffmpeg.exe`), luego pulsa "Comprobar ffmpeg".
- **La transcripción es muy lenta**: usa un modelo más pequeño (`tiny` o `base`) en
  Ajustes, o revisa que la app esté detectando tu GPU NVIDIA (se muestra en la parte
  superior: "GPU NVIDIA (CUDA)" o "CPU").
- **"Instalar.bat" falla al instalar numpy/opencv con errores de compilación
  (`meson`, `Unknown compiler`, `vswhere.exe`, etc.)**: significa que tu Python es
  demasiado nuevo (por ejemplo 3.13+) y esos paquetes aún no publican un instalador
  precompilado para esa versión, así que pip intenta compilarlos desde el código
  fuente y falla porque Windows no trae un compilador de C instalado. Solución:
  instala **Python 3.11 o 3.12** desde python.org (puedes tener varias versiones de
  Python a la vez, no hace falta desinstalar la otra), borra la carpeta
  `backend\.venv` si ya se creó, y vuelve a ejecutar `Instalar.bat`. Si `python` sigue
  apuntando a la versión nueva, edita `Instalar.bat` y cambia la línea
  `set "PYTHON_CMD=python"` por `set "PYTHON_CMD=py -3.11"` (o la versión que hayas
  instalado).
- Los registros técnicos de cada trabajo se guardan en `backend/data/logs/`.
