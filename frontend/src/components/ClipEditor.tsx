import { useEffect, useRef, useState } from "react";
import { api, ClipConfig, Format, Project, StreamType } from "../api";
import CropEditor from "./CropEditor";
import JobProgress from "./JobProgress";

interface Props {
  project: Project;
  clip: ClipConfig;
  onChange: (clip: ClipConfig) => void;
  onApplyToAll: () => void;
}

export default function ClipEditor({ project, clip, onChange, onApplyToAll }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [exportJobId, setExportJobId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const mediaUrl = api.mediaUrl(project.video_id, project.original_filename);

  function set<K extends keyof ClipConfig>(key: K, value: ClipConfig[K]) {
    onChange({ ...clip, [key]: value });
  }

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.currentTime = clip.start;
    function onTime() {
      if (v && v.currentTime >= clip.end) {
        v.pause();
        v.currentTime = clip.start;
      }
    }
    v.addEventListener("timeupdate", onTime);
    return () => v.removeEventListener("timeupdate", onTime);
  }, [clip.start, clip.end]);

  async function persist(next: ClipConfig) {
    setSaving(true);
    try {
      await api.updateClip(project.id, next);
    } finally {
      setSaving(false);
    }
  }

  function updateAndSave(next: ClipConfig) {
    onChange(next);
    persist(next);
  }

  async function handleRangeChange(field: "start" | "end", value: number) {
    let next = { ...clip, [field]: value };
    if (field === "start" && next.start >= next.end) next.end = Math.min(project.duration, next.start + 1);
    if (field === "end" && next.end <= next.start) next.start = Math.max(0, next.end - 1);
    onChange(next);
  }

  async function commitRangeChange() {
    await persist(clip);
    const updated = await api.recomputeSubtitles(project.id, clip.id);
    onChange({ ...clip, subtitles: updated.subtitles, mute_intervals: updated.mute_intervals });
  }

  function updateSubtitle(idx: number, text: string) {
    const subs = clip.subtitles.map((s, i) => (i === idx ? { ...s, text } : s));
    updateAndSave({ ...clip, subtitles: subs });
  }

  function deleteSubtitle(idx: number) {
    const subs = clip.subtitles.filter((_, i) => i !== idx);
    updateAndSave({ ...clip, subtitles: subs });
  }

  async function doExport() {
    await persist(clip);
    const { job_id } = await api.exportClip(project.id, clip.id);
    setExportJobId(job_id);
  }

  return (
    <div className="clip-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div>
          {clip.score != null && <span className="score">Puntuación: {clip.score}/100</span>}
          <span style={{ marginLeft: 10, color: "var(--text-dim)", fontSize: 13 }}>
            {clip.start.toFixed(1)}s – {clip.end.toFixed(1)}s ({(clip.end - clip.start).toFixed(1)}s)
          </span>
        </div>
        {saving && <span style={{ fontSize: 12, color: "var(--text-dim)" }}>Guardando…</span>}
      </div>

      {clip.reasons?.length > 0 && (
        <div className="reasons">Por qué se sugirió: {clip.reasons.join(" · ")}</div>
      )}

      <div className="grid cols-2">
        <div>
          <video ref={videoRef} src={mediaUrl} controls style={{ width: "100%", borderRadius: 10, background: "#000" }} />
          <div className="field" style={{ marginTop: 10 }}>
            <label>Inicio: {clip.start.toFixed(1)}s</label>
            <input
              type="range"
              min={0}
              max={project.duration}
              step={0.1}
              value={clip.start}
              onChange={(e) => handleRangeChange("start", Number(e.target.value))}
              onMouseUp={commitRangeChange}
              onTouchEnd={commitRangeChange}
            />
          </div>
          <div className="field">
            <label>Fin: {clip.end.toFixed(1)}s</label>
            <input
              type="range"
              min={0}
              max={project.duration}
              step={0.1}
              value={clip.end}
              onChange={(e) => handleRangeChange("end", Number(e.target.value))}
              onMouseUp={commitRangeChange}
              onTouchEnd={commitRangeChange}
            />
          </div>
        </div>

        <div>
          <div className="field">
            <label>Formato</label>
            <div className="toggle-group">
              {(["9:16", "1:1", "16:9"] as Format[]).map((f) => (
                <button key={f} className={clip.format === f ? "active" : ""} onClick={() => updateAndSave({ ...clip, format: f })}>
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>Tipo de stream</label>
            <div className="toggle-group">
              {(
                [
                  ["screen_cam", "Pantalla + cámara"],
                  ["cam_only", "Solo cámara"],
                ] as [StreamType, string][]
              ).map(([val, text]) => (
                <button
                  key={val}
                  className={clip.stream_type === val ? "active" : ""}
                  onClick={() => updateAndSave({ ...clip, stream_type: val })}
                >
                  {text}
                </button>
              ))}
            </div>
          </div>

          <div className="field">
            <label>
              <input
                type="checkbox"
                checked={clip.keep_full_vertical_game}
                onChange={(e) => updateAndSave({ ...clip, keep_full_vertical_game: e.target.checked })}
                style={{ width: "auto", marginRight: 8 }}
              />
              Conservar juego vertical completo (fondo extendido difuminado)
            </label>
          </div>

          <div className="field">
            <label>Sincronización de audio: {clip.audio_sync_ms} ms</label>
            <input
              type="range"
              min={-2000}
              max={2000}
              step={10}
              value={clip.audio_sync_ms}
              onChange={(e) => set("audio_sync_ms", Number(e.target.value))}
              onMouseUp={() => persist(clip)}
              onTouchEnd={() => persist(clip)}
            />
          </div>

          <div className="field">
            <label>Usuario de Kick para este clip (opcional)</label>
            <input
              type="text"
              value={clip.kick_username}
              placeholder="Usa el usuario global"
              onChange={(e) => updateAndSave({ ...clip, kick_username: e.target.value })}
            />
          </div>
        </div>
      </div>

      {!clip.keep_full_vertical_game && (
        <div className="grid cols-2" style={{ marginTop: 10 }}>
          <CropEditor
            videoUrl={mediaUrl}
            rect={clip.camera_rect}
            label="Encuadre de la cámara"
            previewTime={clip.start + 0.1}
            onChange={(rect) => updateAndSave({ ...clip, camera_rect: rect })}
          />
          {clip.stream_type === "screen_cam" && (
            <CropEditor
              videoUrl={mediaUrl}
              rect={clip.content_rect}
              label="Encuadre del contenido/pantalla"
              previewTime={clip.start + 0.1}
              onChange={(rect) => updateAndSave({ ...clip, content_rect: rect })}
            />
          )}
        </div>
      )}

      <div className="field" style={{ marginTop: 14 }}>
        <label>
          <input
            type="checkbox"
            checked={clip.subtitles_enabled}
            onChange={(e) => updateAndSave({ ...clip, subtitles_enabled: e.target.checked })}
            style={{ width: "auto", marginRight: 8 }}
          />
          Subtítulos activados
        </label>
        {clip.subtitles_enabled && (
          <div style={{ marginTop: 10, maxHeight: 220, overflowY: "auto" }}>
            {clip.subtitles.map((s, idx) => (
              <div className="subtitle-block" key={idx}>
                <span style={{ fontSize: 12, color: "var(--text-dim)" }}>{s.start.toFixed(1)}s</span>
                <span style={{ fontSize: 12, color: "var(--text-dim)" }}>{s.end.toFixed(1)}s</span>
                <input type="text" value={s.text} onChange={(e) => updateSubtitle(idx, e.target.value)} />
                <button className="btn danger" style={{ padding: "6px 10px" }} onClick={() => deleteSubtitle(idx)}>
                  ✕
                </button>
              </div>
            ))}
            {clip.subtitles.length === 0 && (
              <small className="hint">No hay texto en este intervalo (o aún no se ha analizado el video).</small>
            )}
          </div>
        )}
      </div>

      <div className="btn-row" style={{ marginTop: 16 }}>
        <button className="btn secondary" onClick={onApplyToAll}>
          Aplicar este encuadre a todos
        </button>
        <button className="btn" onClick={doExport} disabled={exportJobId != null && clip.export_status === "processing"}>
          Exportar este clip
        </button>
        {clip.export_status === "done" && clip.export_path && (
          <a className="btn secondary" href={api.downloadClipUrl(project.id, clip.id)} download>
            Descargar MP4
          </a>
        )}
      </div>

      {exportJobId && (
        <div style={{ marginTop: 12 }}>
          <JobProgress
            jobId={exportJobId}
            onCancel={() => api.cancelJob(exportJobId)}
            onDone={() => {
              api.getProject(project.id).then((p) => {
                const updated = p.clips.find((c) => c.id === clip.id);
                if (updated) onChange(updated);
              });
            }}
          />
        </div>
      )}
    </div>
  );
}
