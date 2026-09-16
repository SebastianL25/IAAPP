import { useEffect, useRef, useState } from "react";
import { api, JobStatus } from "../api";

interface Props {
  jobId: string;
  onDone?: (job: JobStatus) => void;
  onCancel?: () => void;
}

function formatTime(seconds: number | null | undefined): string {
  if (seconds == null || Number.isNaN(seconds)) return "--";
  const s = Math.round(seconds);
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${rem.toString().padStart(2, "0")}`;
}

export default function JobProgress({ jobId, onDone, onCancel }: Props) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const doneRef = useRef(false);

  useEffect(() => {
    doneRef.current = false;
    let alive = true;
    const poll = () => {
      api
        .jobStatus(jobId)
        .then((j) => {
          if (!alive) return;
          setJob(j);
          if (["done", "error", "cancelled"].includes(j.status)) {
            if (!doneRef.current) {
              doneRef.current = true;
              onDone?.(j);
            }
            return;
          }
          setTimeout(poll, 1000);
        })
        .catch(() => alive && setTimeout(poll, 2000));
    };
    poll();
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobId]);

  if (!job) return <div className="stage-line">Conectando con el trabajo…</div>;

  return (
    <div>
      <div className="progress-bar">
        <div style={{ width: `${Math.round(job.progress * 100)}%` }} />
      </div>
      <div className="stage-line">
        <span>
          {job.stage} ({Math.round(job.progress * 100)}%)
        </span>
        <span>
          Transcurrido {formatTime(job.elapsed_seconds)}
          {job.eta_seconds != null ? ` · Restante ~${formatTime(job.eta_seconds)}` : ""}
        </span>
      </div>
      {job.status === "error" && <div className="error-box">Error: {job.error}</div>}
      {job.status === "processing" && onCancel && (
        <button className="btn danger" style={{ marginTop: 8 }} onClick={onCancel}>
          Cancelar
        </button>
      )}
    </div>
  );
}
