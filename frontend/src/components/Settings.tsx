import { useEffect, useState } from "react";
import { api } from "../api";

export default function Settings({ onClose }: { onClose: () => void }) {
  const [ffmpegPath, setFfmpegPath] = useState("");
  const [whisperModel, setWhisperModel] = useState("medium");
  const [whisperDevice, setWhisperDevice] = useState("auto");
  const [censoredWords, setCensoredWords] = useState("");
  const [checking, setChecking] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings().then((s: any) => {
      setFfmpegPath(s.ffmpeg_path || "");
      setWhisperModel(s.whisper_model || "medium");
      setWhisperDevice(s.whisper_device || "auto");
      setCensoredWords((s.censored_words || []).join(", "));
    });
  }, []);

  async function save() {
    await api.updateSettings({
      ffmpeg_path: ffmpegPath,
      whisper_model: whisperModel,
      whisper_device: whisperDevice,
      censored_words: censoredWords.split(",").map((w) => w.trim()).filter(Boolean),
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function checkFfmpeg() {
    setChecking("Comprobando…");
    const res = await fetch("/api/system/check-ffmpeg", { method: "POST" }).then((r) => r.json());
    setChecking(res.ok ? `OK: ${res.message}` : `Error: ${res.message}`);
  }

  return (
    <div className="card" style={{ position: "relative" }}>
      <button className="btn secondary" style={{ position: "absolute", right: 16, top: 16 }} onClick={onClose}>
        Cerrar
      </button>
      <h2>Ajustes</h2>

      <div className="field">
        <label>Ruta absoluta de ffmpeg.exe (déjalo vacío para usar el PATH del sistema)</label>
        <input type="text" value={ffmpegPath} onChange={(e) => setFfmpegPath(e.target.value)} placeholder="C:\\ffmpeg\\bin\\ffmpeg.exe" />
        <div className="btn-row" style={{ marginTop: 8 }}>
          <button className="btn secondary" onClick={checkFfmpeg}>
            Comprobar ffmpeg
          </button>
          {checking && <span style={{ alignSelf: "center", fontSize: 13, color: "var(--text-dim)" }}>{checking}</span>}
        </div>
      </div>

      <div className="grid cols-2">
        <div className="field">
          <label>Modelo de transcripción (Whisper)</label>
          <select value={whisperModel} onChange={(e) => setWhisperModel(e.target.value)}>
            <option value="tiny">tiny (más rápido, menos preciso)</option>
            <option value="base">base</option>
            <option value="small">small</option>
            <option value="medium">medium (recomendado)</option>
            <option value="large-v3">large-v3 (más preciso, más lento)</option>
          </select>
          <small className="hint">
            La primera vez que se use un modelo, se descargará automáticamente (requiere conexión a internet solo
            para esa descarga; el procesamiento del video siempre ocurre en tu computador).
          </small>
        </div>
        <div className="field">
          <label>Dispositivo de procesamiento</label>
          <select value={whisperDevice} onChange={(e) => setWhisperDevice(e.target.value)}>
            <option value="auto">Automático (usa GPU NVIDIA si está disponible)</option>
            <option value="cuda">Forzar GPU (CUDA)</option>
            <option value="cpu">Forzar CPU</option>
          </select>
        </div>
      </div>

      <div className="field">
        <label>Palabras censuradas (separadas por comas)</label>
        <textarea rows={3} value={censoredWords} onChange={(e) => setCensoredWords(e.target.value)} />
        <small className="hint">Se reemplazan por asteriscos en los subtítulos y se silencia solo ese instante de audio.</small>
      </div>

      <button className="btn" onClick={save}>
        Guardar ajustes
      </button>
      {saved && <span style={{ marginLeft: 10, color: "var(--lime)" }}>Guardado</span>}
    </div>
  );
}
