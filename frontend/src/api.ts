export type Format = "9:16" | "1:1" | "16:9";
export type StreamType = "screen_cam" | "cam_only";

export interface CropRect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface SubtitleBlock {
  start: number;
  end: number;
  text: string;
}

export interface ClipConfig {
  id: string;
  start: number;
  end: number;
  format: Format;
  stream_type: StreamType;
  camera_rect: CropRect;
  content_rect: CropRect;
  keep_full_vertical_game: boolean;
  audio_sync_ms: number;
  subtitles_enabled: boolean;
  subtitles: SubtitleBlock[];
  mute_intervals: number[][];
  kick_username: string;
  score?: number;
  reasons: string[];
  export_status: "idle" | "queued" | "processing" | "done" | "error" | "cancelled";
  export_progress: number;
  export_path?: string | null;
  export_error?: string | null;
}

export interface ProjectConfig {
  format: Format;
  clip_duration: number;
  clip_count: number;
  stream_type: StreamType;
  camera_rect: CropRect;
  kick_username: string;
  subtitles_enabled: boolean;
}

export interface Project {
  id: string;
  video_id: string;
  original_filename: string;
  duration: number;
  width: number;
  height: number;
  fps: number;
  config: ProjectConfig;
  clips: ClipConfig[];
  analysis_status: "idle" | "queued" | "processing" | "done" | "error" | "cancelled";
  analysis_job_id?: string | null;
  created_at: string;
}

export interface JobStatus {
  id: string;
  type: string;
  project_id: string | null;
  status: "queued" | "processing" | "done" | "error" | "cancelled";
  stage: string;
  progress: number;
  error: string | null;
  elapsed_seconds: number;
  eta_seconds: number | null;
  result: Record<string, unknown> | null;
}

export interface SystemStatus {
  ffmpeg_ok: boolean;
  ffmpeg_path: string | null;
  ffprobe_ok: boolean;
  ffprobe_path: string | null;
  gpu: { cuda_available: boolean; active_device: string; label: string };
  whisper_model: string;
  model_likely_downloaded: boolean;
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = res.statusText;
    try {
      const data = await res.json();
      message = data.detail || message;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }
  return res.json();
}

export const api = {
  systemStatus: () => fetch("/api/system/status").then((r) => handle<SystemStatus>(r)),
  updateSettings: (patch: Record<string, unknown>) =>
    fetch("/api/system/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }).then((r) => handle(r)),
  getSettings: () => fetch("/api/system/settings").then((r) => handle<Record<string, unknown>>(r)),

  upload: (file: File, onProgress?: (pct: number) => void) =>
    new Promise<{ video_id: string; filename: string; duration: number; width: number; height: number; fps: number }>(
      (resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", "/api/upload");
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && onProgress) onProgress((e.loaded / e.total) * 100);
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve(JSON.parse(xhr.responseText));
          } else {
            try {
              reject(new Error(JSON.parse(xhr.responseText).detail || xhr.statusText));
            } catch {
              reject(new Error(xhr.statusText));
            }
          }
        };
        xhr.onerror = () => reject(new Error("Error de red durante la subida"));
        const form = new FormData();
        form.append("file", file);
        xhr.send(form);
      }
    ),

  createProject: (video_id: string, config: ProjectConfig) =>
    fetch(`/api/projects?video_id=${encodeURIComponent(video_id)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }).then((r) => handle<Project>(r)),

  getProject: (id: string) => fetch(`/api/projects/${id}`).then((r) => handle<Project>(r)),
  listProjects: () => fetch(`/api/projects`).then((r) => handle<Project[]>(r)),
  updateProjectConfig: (id: string, config: ProjectConfig) =>
    fetch(`/api/projects/${id}/config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    }).then((r) => handle<Project>(r)),

  analyze: (projectId: string) =>
    fetch(`/api/projects/${projectId}/analyze`, { method: "POST" }).then((r) => handle<{ job_id: string }>(r)),

  updateClip: (projectId: string, clip: ClipConfig) =>
    fetch(`/api/projects/${projectId}/clips/${clip.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(clip),
    }).then((r) => handle<ClipConfig>(r)),

  applyToAll: (projectId: string, clipId: string) =>
    fetch(`/api/projects/${projectId}/clips/${clipId}/apply-to-all`, { method: "POST" }).then((r) =>
      handle<Project>(r)
    ),

  recomputeSubtitles: (projectId: string, clipId: string) =>
    fetch(`/api/projects/${projectId}/clips/${clipId}/recompute-subtitles`, { method: "POST" }).then((r) =>
      handle<ClipConfig>(r)
    ),

  exportClip: (projectId: string, clipId: string) =>
    fetch(`/api/projects/${projectId}/clips/${clipId}/export`, { method: "POST" }).then((r) =>
      handle<{ job_id: string }>(r)
    ),

  exportAll: (projectId: string) =>
    fetch(`/api/projects/${projectId}/export-all`, { method: "POST" }).then((r) =>
      handle<{ jobs: { clip_id: string; job_id: string }[] }>(r)
    ),

  downloadClipUrl: (projectId: string, clipId: string) => `/api/projects/${projectId}/clips/${clipId}/download`,
  downloadZipUrl: (projectId: string) => `/api/projects/${projectId}/export/zip`,

  jobStatus: (jobId: string) => fetch(`/api/jobs/${jobId}`).then((r) => handle<JobStatus>(r)),
  cancelJob: (jobId: string) => fetch(`/api/jobs/${jobId}/cancel`, { method: "POST" }).then((r) => handle(r)),

  mediaUrl: (videoId: string, filename: string) => `/media/uploads/${videoId}/${encodeURIComponent(filename)}`,
};
