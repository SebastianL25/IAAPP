import { useEffect, useState } from "react";
import { api, ClipConfig, Project, ProjectConfig } from "./api";
import ConfigForm from "./components/ConfigForm";
import Uploader from "./components/Uploader";
import SystemBadge from "./components/SystemBadge";
import JobProgress from "./components/JobProgress";
import ClipEditor from "./components/ClipEditor";
import Settings from "./components/Settings";

const LAST_PROJECT_KEY = "xslou_last_project_id";

const DEFAULT_CONFIG: ProjectConfig = {
  format: "9:16",
  clip_duration: 30,
  clip_count: 5,
  stream_type: "screen_cam",
  camera_rect: { x: 0.02, y: 0.02, w: 0.32, h: 0.32 },
  kick_username: "",
  subtitles_enabled: true,
};

export default function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [config, setConfig] = useState<ProjectConfig>(DEFAULT_CONFIG);
  const [uploadInfo, setUploadInfo] = useState<{ video_id: string; filename: string; duration: number } | null>(null);
  const [analyzeJobId, setAnalyzeJobId] = useState<string | null>(null);
  const [activeClipId, setActiveClipId] = useState<string | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingSaved, setLoadingSaved] = useState(true);

  useEffect(() => {
    const savedId = localStorage.getItem(LAST_PROJECT_KEY);
    if (savedId) {
      api
        .getProject(savedId)
        .then((p) => {
          setProject(p);
          setConfig(p.config);
          if (p.analysis_job_id && p.analysis_status === "processing") setAnalyzeJobId(p.analysis_job_id);
          if (p.clips.length > 0) setActiveClipId(p.clips[0].id);
        })
        .catch(() => localStorage.removeItem(LAST_PROJECT_KEY))
        .finally(() => setLoadingSaved(false));
    } else {
      setLoadingSaved(false);
    }
  }, []);

  async function handleUploaded(info: { video_id: string; filename: string; duration: number }) {
    setError(null);
    setUploadInfo(info);
  }

  async function handleAnalyze() {
    setError(null);
    try {
      let p = project;
      if (!p) {
        if (!uploadInfo) return;
        p = await api.createProject(uploadInfo.video_id, config);
      } else {
        p = await api.updateProjectConfig(p.id, config);
      }
      setProject(p);
      localStorage.setItem(LAST_PROJECT_KEY, p.id);
      const { job_id } = await api.analyze(p.id);
      setAnalyzeJobId(job_id);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function refreshProjectAfterAnalysis() {
    if (!project) return;
    const p = await api.getProject(project.id);
    setProject(p);
    if (p.clips.length > 0) setActiveClipId(p.clips[0].id);
    setAnalyzeJobId(null);
  }

  function updateClipLocal(clip: ClipConfig) {
    if (!project) return;
    setProject({ ...project, clips: project.clips.map((c) => (c.id === clip.id ? clip : c)) });
  }

  async function applyToAll(clipId: string) {
    if (!project) return;
    const p = await api.applyToAll(project.id, clipId);
    setProject(p);
  }

  async function startNewProject() {
    localStorage.removeItem(LAST_PROJECT_KEY);
    setProject(null);
    setUploadInfo(null);
    setAnalyzeJobId(null);
    setActiveClipId(null);
    setConfig(DEFAULT_CONFIG);
  }

  const [exportAllJobs, setExportAllJobs] = useState<{ clip_id: string; job_id: string }[]>([]);

  async function handleExportAll() {
    if (!project) return;
    const res = await api.exportAll(project.id);
    setExportAllJobs(res.jobs);
  }

  if (loadingSaved) return null;

  return (
    <div className="app-shell">
      <div className="app-header">
        <div className="brand">
          <span className="dot" />
          xSlou Clips AI
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <SystemBadge />
          <button className="btn secondary" onClick={() => setShowSettings((s) => !s)}>
            Ajustes
          </button>
          {project && (
            <button className="btn secondary" onClick={startNewProject}>
              Nuevo proyecto
            </button>
          )}
        </div>
      </div>

      {error && <div className="error-box">{error}</div>}
      {showSettings && <Settings onClose={() => setShowSettings(false)} />}

      {!project && (
        <div className="card">
          <h2>
            <span className="step">1</span>Sube tu video
          </h2>
          <Uploader onUploaded={handleUploaded} />
        </div>
      )}

      {!project && uploadInfo && (
        <div className="card">
          <h2>
            <span className="step">2</span>Configura los clips
          </h2>
          <ConfigForm config={config} onChange={setConfig} />
          <div className="btn-row" style={{ marginTop: 16 }}>
            <button className="btn" onClick={handleAnalyze}>
              Analizar stream con IA
            </button>
          </div>
        </div>
      )}

      {project && !analyzeJobId && project.analysis_status !== "done" && (
        <div className="card">
          <h2>
            <span className="step">2</span>Configuración del proyecto
          </h2>
          <ConfigForm config={config} onChange={setConfig} />
          <div className="btn-row" style={{ marginTop: 16 }}>
            <button className="btn" onClick={handleAnalyze}>
              Analizar stream con IA
            </button>
          </div>
        </div>
      )}

      {analyzeJobId && (
        <div className="card">
          <h2>
            <span className="step">3</span>Analizando con IA…
          </h2>
          <JobProgress
            jobId={analyzeJobId}
            onCancel={() => api.cancelJob(analyzeJobId)}
            onDone={refreshProjectAfterAnalysis}
          />
        </div>
      )}

      {project && project.analysis_status === "done" && project.clips.length > 0 && (
        <div className="card">
          <h2>
            <span className="step">4</span>Revisa y edita los momentos sugeridos
          </h2>
          <div className="disclaimer">
            La puntuación es una estimación basada en voz, energía de audio, rostros y movimiento. No garantiza que
            un clip se vuelva viral: úsala como guía, no como verdad absoluta.
          </div>
          <div className="tabs">
            {project.clips.map((c, i) => (
              <button key={c.id} className={activeClipId === c.id ? "active" : ""} onClick={() => setActiveClipId(c.id)}>
                Clip {i + 1} {c.export_status === "done" ? "✓" : ""}
              </button>
            ))}
          </div>
          {project.clips
            .filter((c) => c.id === activeClipId)
            .map((c) => (
              <ClipEditor
                key={c.id}
                project={project}
                clip={c}
                onChange={updateClipLocal}
                onApplyToAll={() => applyToAll(c.id)}
              />
            ))}

          <div className="btn-row" style={{ marginTop: 10 }}>
            <button className="btn" onClick={handleExportAll}>
              Exportar todos
            </button>
            <a className="btn secondary" href={api.downloadZipUrl(project.id)}>
              Descargar ZIP
            </a>
          </div>

          {exportAllJobs.length > 0 && (
            <div style={{ marginTop: 16 }}>
              {exportAllJobs.map((j) => (
                <div key={j.job_id} style={{ marginBottom: 10 }}>
                  <div style={{ fontSize: 12, color: "var(--text-dim)", marginBottom: 4 }}>
                    Clip {project.clips.findIndex((c) => c.id === j.clip_id) + 1}
                  </div>
                  <JobProgress jobId={j.job_id} onCancel={() => api.cancelJob(j.job_id)} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {project && project.analysis_status === "done" && project.clips.length === 0 && (
        <div className="card">
          <div className="error-box">
            No se encontraron momentos claros con la configuración actual. Prueba con una duración de clip distinta
            o revisa que el video tenga audio.
          </div>
        </div>
      )}
    </div>
  );
}
