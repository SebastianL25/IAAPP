import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../services/api";
import type { SourceVideo } from "../types/api";

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  importing: "Importando...",
  ready: "Listo",
  error: "Error",
  duplicate: "Duplicado",
};

const STATUS_COLOR: Record<string, string> = {
  pending: "bg-slate-600",
  importing: "bg-amber-600",
  ready: "bg-emerald-600",
  error: "bg-red-600",
  duplicate: "bg-slate-600",
};

function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function formatSize(bytes: number): string {
  const mb = bytes / (1024 * 1024);
  return mb > 1024 ? `${(mb / 1024).toFixed(2)} GB` : `${mb.toFixed(1)} MB`;
}

export default function VideoCard({ video, projectId }: { video: SourceVideo; projectId: string }) {
  const queryClient = useQueryClient();
  const [showPlayer, setShowPlayer] = useState(false);

  const analyzeMutation = useMutation({
    mutationFn: () => api.analyzeVideo(video.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["jobs", projectId] }),
  });

  return (
    <div className="bg-surface-raised border border-surface-border rounded-xl overflow-hidden flex flex-col">
      <div className="aspect-video bg-black flex items-center justify-center relative group">
        {showPlayer ? (
          <video
            className="w-full h-full"
            controls
            preload="metadata"
            src={video.has_proxy ? api.videoProxyUrl(video.id) : api.videoStreamUrl(video.id)}
          />
        ) : video.has_thumbnail ? (
          <button className="w-full h-full relative" onClick={() => setShowPlayer(true)}>
            <img src={api.videoThumbnailUrl(video.id)} alt={video.original_filename} className="w-full h-full object-cover" />
            <span className="absolute inset-0 flex items-center justify-center bg-black/0 group-hover:bg-black/30 transition-colors text-2xl opacity-0 group-hover:opacity-100">
              ▶
            </span>
          </button>
        ) : (
          <button className="text-slate-600 text-xs" onClick={() => setShowPlayer(true)}>
            Reproducir
          </button>
        )}
      </div>
      <div className="p-3 flex-1 flex flex-col gap-1">
        <div className="flex items-center justify-between gap-2">
          <p className="font-medium text-sm truncate" title={video.original_filename}>
            {video.original_filename}
          </p>
          <span className={`text-[10px] px-2 py-0.5 rounded-full shrink-0 ${STATUS_COLOR[video.import_status]}`}>
            {STATUS_LABEL[video.import_status] ?? video.import_status}
          </span>
        </div>
        {video.video_metadata && (
          <p className="text-xs text-slate-400">
            {formatDuration(video.video_metadata.duration_seconds)} · {video.video_metadata.width}x
            {video.video_metadata.height} · {video.video_metadata.fps.toFixed(0)}fps · {formatSize(video.size_bytes)}
          </p>
        )}
        {video.error_message && <p className="text-xs text-red-400">{video.error_message}</p>}
        <div className="mt-auto pt-2">
          <button
            disabled={analyzeMutation.isPending}
            onClick={() => analyzeMutation.mutate()}
            className="text-xs w-full bg-surface border border-surface-border rounded px-2 py-1.5 hover:border-accent disabled:opacity-40"
          >
            {analyzeMutation.isPending ? "Encolando..." : "Re-analizar"}
          </button>
        </div>
      </div>
    </div>
  );
}
