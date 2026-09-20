import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../services/api";
import type { ClipCandidate, SourceVideo } from "../../types/api";

const ASPECT_RATIOS = ["9:16", "16:9", "1:1", "4:5"];
const PRESETS = ["tiktok", "reels", "shorts", "facebook", "x", "master"];

function scoreColor(score: number): string {
  if (score >= 75) return "text-emerald-400 border-emerald-400";
  if (score >= 50) return "text-amber-400 border-amber-400";
  return "text-slate-400 border-slate-500";
}

export default function ClipCard({ clip, video }: { clip: ClipCandidate; video?: SourceVideo }) {
  const queryClient = useQueryClient();
  const [start, setStart] = useState(clip.start_time);
  const [end, setEnd] = useState(clip.end_time);
  const [showExport, setShowExport] = useState(false);
  const [aspectRatio, setAspectRatio] = useState("9:16");
  const [preset, setPreset] = useState("tiktok");
  const [burnCaptions, setBurnCaptions] = useState(true);
  const [exportJobId, setExportJobId] = useState<string | null>(null);

  const invalidateClips = () => queryClient.invalidateQueries({ queryKey: ["clips", clip.project_id] });

  const updateMutation = useMutation({
    mutationFn: (payload: { start_time?: number; end_time?: number }) => api.updateClip(clip.id, payload),
    onSuccess: invalidateClips,
  });

  const approveMutation = useMutation({ mutationFn: () => api.approveClip(clip.id), onSuccess: invalidateClips });
  const discardMutation = useMutation({ mutationFn: () => api.discardClip(clip.id), onSuccess: invalidateClips });

  const exportMutation = useMutation({
    mutationFn: () => api.exportClip(clip.id, { aspect_ratio: aspectRatio, preset, burn_captions: burnCaptions }),
    onSuccess: (job) => setExportJobId(job.id),
  });

  const exportStatusQuery = useQuery({
    queryKey: ["export", exportJobId],
    queryFn: () => api.getExport(exportJobId as string),
    enabled: !!exportJobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "done" || status === "error" ? false : 1500;
    },
  });

  const durationLabel = `${(end - start).toFixed(1)}s`;

  return (
    <div className="bg-surface-raised border border-surface-border rounded-xl p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium">{clip.title || clip.hook || "Clip sin titulo"}</p>
          <p className="text-xs text-slate-500">
            {video?.original_filename ?? "video"} · {clip.category} · {durationLabel}
          </p>
        </div>
        <span className={`text-sm font-semibold border rounded-full w-10 h-10 flex items-center justify-center shrink-0 ${scoreColor(clip.viral_score)}`}>
          {clip.viral_score}
        </span>
      </div>

      <p className="text-xs text-slate-400">{clip.reason}</p>

      <div className="flex flex-wrap gap-1">
        {clip.detected_events.map((ev) => (
          <span key={ev} className="text-[10px] bg-surface border border-surface-border rounded-full px-2 py-0.5 text-slate-400">
            {ev}
          </span>
        ))}
      </div>

      <div className="flex items-center gap-2 text-xs mt-1">
        <label className="text-slate-400">Inicio</label>
        <input
          type="number"
          step="0.1"
          className="w-20 bg-surface border border-surface-border rounded px-2 py-1"
          value={start}
          onChange={(e) => setStart(Number(e.target.value))}
          onBlur={() => updateMutation.mutate({ start_time: start })}
        />
        <label className="text-slate-400">Fin</label>
        <input
          type="number"
          step="0.1"
          className="w-20 bg-surface border border-surface-border rounded px-2 py-1"
          value={end}
          onChange={(e) => setEnd(Number(e.target.value))}
          onBlur={() => updateMutation.mutate({ end_time: end })}
        />
        <button
          className="text-slate-400 hover:text-accent ml-auto"
          title="Ampliar contexto (+5s antes y despues)"
          onClick={() => {
            const newStart = Math.max(0, start - 5);
            const newEnd = end + 5;
            setStart(newStart);
            setEnd(newEnd);
            updateMutation.mutate({ start_time: newStart, end_time: newEnd });
          }}
        >
          ⤢ Ampliar
        </button>
      </div>

      <div className="flex gap-2 mt-1">
        <button
          disabled={clip.status === "approved"}
          onClick={() => approveMutation.mutate()}
          className="flex-1 text-xs bg-emerald-700/30 border border-emerald-700 rounded px-2 py-1.5 hover:bg-emerald-700/50 disabled:opacity-40"
        >
          Aprobar
        </button>
        <button
          disabled={clip.status === "discarded"}
          onClick={() => discardMutation.mutate()}
          className="flex-1 text-xs bg-red-700/20 border border-red-800 rounded px-2 py-1.5 hover:bg-red-700/40 disabled:opacity-40"
        >
          Descartar
        </button>
        <button
          onClick={() => setShowExport((v) => !v)}
          className="flex-1 text-xs bg-accent/20 border border-accent rounded px-2 py-1.5 hover:bg-accent/40"
        >
          Exportar
        </button>
      </div>

      {showExport && (
        <div className="mt-2 border-t border-surface-border pt-3 flex flex-col gap-2">
          <div className="flex gap-2 text-xs">
            <select
              className="flex-1 bg-surface border border-surface-border rounded px-2 py-1"
              value={aspectRatio}
              onChange={(e) => setAspectRatio(e.target.value)}
            >
              {ASPECT_RATIOS.map((ar) => (
                <option key={ar} value={ar}>
                  {ar}
                </option>
              ))}
            </select>
            <select
              className="flex-1 bg-surface border border-surface-border rounded px-2 py-1"
              value={preset}
              onChange={(e) => setPreset(e.target.value)}
            >
              {PRESETS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-2 text-xs text-slate-400">
            <input type="checkbox" checked={burnCaptions} onChange={(e) => setBurnCaptions(e.target.checked)} />
            Quemar subtitulos
          </label>
          <button
            disabled={exportMutation.isPending}
            onClick={() => exportMutation.mutate()}
            className="text-xs bg-accent hover:bg-accent-hover rounded px-3 py-1.5 disabled:opacity-40"
          >
            {exportMutation.isPending ? "Encolando..." : "Generar MP4 vertical"}
          </button>

          {exportStatusQuery.data && (
            <div className="text-xs">
              <p className="text-slate-400">
                Estado: {exportStatusQuery.data.status} ({exportStatusQuery.data.progress_percent.toFixed(0)}%)
              </p>
              {exportStatusQuery.data.status === "done" && exportStatusQuery.data.output_path && (
                <a
                  className="text-accent hover:underline"
                  href={api.exportDownloadUrl(exportStatusQuery.data.id)}
                  download
                >
                  Descargar clip exportado
                </a>
              )}
              {exportStatusQuery.data.status === "error" && (
                <p className="text-red-400">{exportStatusQuery.data.error_message}</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
