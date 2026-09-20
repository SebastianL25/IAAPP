import type {
  ClipCandidate,
  ExportJob,
  Project,
  ProcessingJob,
  SourceVideo,
  VideoAnalysis,
} from "../types/api";

const BASE = "/api";

export class ApiError extends Error {
  code: string;
  status: number;
  constructor(message: string, code: string, status: number) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: options?.body instanceof FormData ? undefined : { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let code = "UNKNOWN";
    let message = res.statusText;
    try {
      const data = await res.json();
      code = data?.error?.code ?? code;
      message = data?.error?.message ?? message;
    } catch {
      /* respuesta sin json */
    }
    throw new ApiError(message, code, res.status);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  // Proyectos
  listProjects: () => request<Project[]>("/projects"),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (payload: { name: string; game_or_category?: string; target_platform?: string; language?: string }) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify(payload) }),
  updateProject: (id: string, payload: Partial<Project>) =>
    request<Project>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: (id: string) => request<{ ok: boolean }>(`/projects/${id}`, { method: "DELETE" }),

  // Videos
  listVideosByProject: (projectId: string) =>
    request<SourceVideo[]>(`/videos?project_id=${projectId}`).catch(() => [] as SourceVideo[]),
  getVideo: (id: string) => request<SourceVideo>(`/videos/${id}`),
  importFiles: (projectId: string, files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    return request<SourceVideo[]>(`/videos/import?project_id=${projectId}`, {
      method: "POST",
      body: form,
    });
  },
  importByPath: (projectId: string, path: string) =>
    request<SourceVideo>("/videos/import-path", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, path }),
    }),
  importFolder: (projectId: string, folderPath: string) =>
    request<SourceVideo[]>("/videos/import-folder", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, folder_path: folderPath }),
    }),
  analyzeVideo: (id: string) => request<{ job_id: string }>(`/videos/${id}/analyze`, { method: "POST" }),
  getAnalysis: (id: string) => request<VideoAnalysis>(`/videos/${id}/analysis`),
  deleteVideo: (id: string) => request<{ ok: boolean }>(`/videos/${id}`, { method: "DELETE" }),

  // Jobs
  listJobs: (projectId?: string) =>
    request<ProcessingJob[]>(`/jobs${projectId ? `?project_id=${projectId}` : ""}`),
  retryJob: (id: string) => request<{ ok: boolean }>(`/jobs/${id}/retry`, { method: "POST" }),
  cancelJob: (id: string) => request<{ ok: boolean }>(`/jobs/${id}/cancel`, { method: "POST" }),
  pauseQueue: () => request<{ ok: boolean }>("/jobs/pause-queue", { method: "POST" }),
  resumeQueue: () => request<{ ok: boolean }>("/jobs/resume-queue", { method: "POST" }),

  // Clips
  listClips: (projectId: string) => request<ClipCandidate[]>(`/clips?project_id=${projectId}`),
  updateClip: (id: string, payload: { start_time?: number; end_time?: number; title?: string }) =>
    request<ClipCandidate>(`/clips/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  approveClip: (id: string) => request<ClipCandidate>(`/clips/${id}/approve`, { method: "POST", body: JSON.stringify({ label: "approved" }) }),
  discardClip: (id: string, label = "discarded") =>
    request<ClipCandidate>(`/clips/${id}/discard`, { method: "POST", body: JSON.stringify({ label }) }),
  exportClip: (id: string, payload: { aspect_ratio: string; preset: string; burn_captions: boolean }) =>
    request<ExportJob>(`/clips/${id}/export`, { method: "POST", body: JSON.stringify(payload) }),

  // Exports
  getExport: (id: string) => request<ExportJob>(`/exports/${id}`),
  listExportsForClip: (clipId: string) => request<ExportJob[]>(`/exports?clip_id=${clipId}`),

  videoStreamUrl: (id: string) => `${BASE}/videos/${id}/stream`,
  videoProxyUrl: (id: string) => `${BASE}/videos/${id}/proxy`,
  videoThumbnailUrl: (id: string) => `${BASE}/videos/${id}/thumbnail`,
  exportDownloadUrl: (id: string) => `${BASE}/exports/${id}/download`,
};
