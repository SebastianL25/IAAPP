import type { CropRect, Format, ProjectConfig, StreamType } from "../api";

interface Props {
  config: ProjectConfig;
  onChange: (config: ProjectConfig) => void;
  videoUrl?: string;
}

const CAMERA_PRESETS: { label: string; rect: CropRect }[] = [
  { label: "Arriba izquierda", rect: { x: 0.02, y: 0.02, w: 0.32, h: 0.32 } },
  { label: "Arriba derecha", rect: { x: 0.66, y: 0.02, w: 0.32, h: 0.32 } },
  { label: "Abajo izquierda", rect: { x: 0.02, y: 0.66, w: 0.32, h: 0.32 } },
  { label: "Abajo derecha", rect: { x: 0.66, y: 0.66, w: 0.32, h: 0.32 } },
];

export default function ConfigForm({ config, onChange }: Props) {
  function set<K extends keyof ProjectConfig>(key: K, value: ProjectConfig[K]) {
    onChange({ ...config, [key]: value });
  }

  return (
    <div>
      <div className="grid cols-3">
        <div className="field">
          <label>Formato de salida</label>
          <div className="toggle-group">
            {(["9:16", "1:1", "16:9"] as Format[]).map((f) => (
              <button key={f} className={config.format === f ? "active" : ""} onClick={() => set("format", f)}>
                {f}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Duración de cada clip: {config.clip_duration}s</label>
          <input
            type="range"
            min={5}
            max={180}
            value={config.clip_duration}
            onChange={(e) => set("clip_duration", Number(e.target.value))}
          />
        </div>

        <div className="field">
          <label>Cantidad de clips: {config.clip_count}</label>
          <input
            type="range"
            min={1}
            max={10}
            value={config.clip_count}
            onChange={(e) => set("clip_count", Number(e.target.value))}
          />
        </div>
      </div>

      <div className="grid cols-2">
        <div className="field">
          <label>Tipo de stream</label>
          <div className="toggle-group">
            {(
              [
                ["screen_cam", "Pantalla + cámara"],
                ["cam_only", "Solo cámara"],
              ] as [StreamType, string][]
            ).map(([val, text]) => (
              <button key={val} className={config.stream_type === val ? "active" : ""} onClick={() => set("stream_type", val)}>
                {text}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label>Usuario de Kick (para la marca de agua)</label>
          <input
            type="text"
            placeholder="tuusuario"
            value={config.kick_username}
            onChange={(e) => set("kick_username", e.target.value)}
          />
          <small className="hint">
            Se mostrará como KICK.COM/{config.kick_username.toUpperCase() || "USUARIO"}
          </small>
        </div>
      </div>

      <div className="field">
        <label>Posición aproximada de la cámara</label>
        <div className="toggle-group">
          {CAMERA_PRESETS.map((p) => (
            <button key={p.label} onClick={() => set("camera_rect", p.rect)}>
              {p.label}
            </button>
          ))}
        </div>
        <small className="hint">Podrás ajustarla con precisión (arrastrando) en cada clip durante la edición.</small>
      </div>

      <div className="field">
        <label>
          <input
            type="checkbox"
            checked={config.subtitles_enabled}
            onChange={(e) => set("subtitles_enabled", e.target.checked)}
            style={{ width: "auto", marginRight: 8 }}
          />
          Subtítulos automáticos en español
        </label>
      </div>
    </div>
  );
}
