import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../services/api";
import { useJobsStore } from "../../stores/jobsStore";
import type { ProcessingJob } from "../../types/api";

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-slate-600",
  running: "bg-accent",
  paused: "bg-amber-600",
  done: "bg-emerald-600",
  error: "bg-red-600",
  cancelled: "bg-slate-600",
};

const JOB_TYPE_LABEL: Record<string, string> = {
  analyze: "Analisis completo",
  proxy: "Generando proxy",
  transcribe: "Transcripcion",
  export: "Exportacion",
};

function mergeLive(job: ProcessingJob, live: ReturnType<typeof useJobsStore.getState>["jobsById"]): ProcessingJob {
  const update = live[job.id];
  if (!update) return job;
  return {
    ...job,
    status: (update.status as ProcessingJob["status"]) ?? job.status,
    progress_percent: update.progress_percent ?? job.progress_percent,
    stage_message: update.stage_message ?? job.stage_message,
  };
}

export default function ProcessingQueuePanel({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const jobsById = useJobsStore((s) => s.jobsById);

  const jobsQuery = useQuery({
    queryKey: ["jobs", projectId],
    queryFn: () => api.listJobs(projectId),
    refetchInterval: 4000,
  });

  const retryMutation = useMutation({
    mutationFn: (id: string) => api.retryJob(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs", projectId] }),
  });
  const cancelMutation = useMutation({
    mutationFn: (id: string) => api.cancelJob(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs", projectId] }),
  });
  const pauseMutation = useMutation({ mutationFn: api.pauseQueue });
  const resumeMutation = useMutation({ mutationFn: api.resumeQueue });

  const jobs = (jobsQuery.data ?? []).map((j) => mergeLive(j, jobsById));
  const activeJobs = jobs.filter((j) => j.status === "running" || j.status === "pending");

  return (
    <div className="bg-surface-raised border border-surface-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-medium">Cola de procesamiento</h3>
        <div className="flex gap-2">
          <button
            className="text-xs bg-surface border border-surface-border rounded px-2 py-1 hover:border-accent"
            onClick={() => pauseMutation.mutate()}
          >
            Pausar cola
          </button>
          <button
            className="text-xs bg-surface border border-surface-border rounded px-2 py-1 hover:border-accent"
            onClick={() => resumeMutation.mutate()}
          >
            Reanudar
          </button>
        </div>
      </div>

      {jobs.length === 0 && <p className="text-sm text-slate-500">Sin trabajos todavia.</p>}

      <div className="flex flex-col gap-2 max-h-72 overflow-y-auto">
        {jobs.map((job) => (
          <div key={job.id} className="bg-surface rounded-lg p-3 border border-surface-border">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="font-medium">{JOB_TYPE_LABEL[job.job_type] ?? job.job_type}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded-full ${STATUS_COLOR[job.status]}`}>{job.status}</span>
            </div>
            <div className="w-full h-1.5 bg-surface-border rounded-full overflow-hidden">
              <div
                className="h-full bg-accent transition-all"
                style={{ width: `${Math.max(2, job.progress_percent)}%` }}
              />
            </div>
            <p className="text-xs text-slate-400 mt-1 truncate">{job.stage_message || job.error_message}</p>
            <div className="flex gap-2 mt-2">
              {job.status === "error" && (
                <button
                  className="text-xs text-accent hover:underline"
                  onClick={() => retryMutation.mutate(job.id)}
                >
                  Reintentar
                </button>
              )}
              {(job.status === "pending" || job.status === "running") && (
                <button
                  className="text-xs text-slate-400 hover:underline"
                  onClick={() => cancelMutation.mutate(job.id)}
                >
                  Cancelar
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      {activeJobs.length > 0 && (
        <p className="text-xs text-slate-500 mt-2">{activeJobs.length} trabajo(s) activos</p>
      )}
    </div>
  );
}
