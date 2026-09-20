import { useQuery } from "@tanstack/react-query";

import { api } from "../../services/api";
import type { SourceVideo } from "../../types/api";
import ClipCard from "./ClipCard";

export default function ClipList({ projectId, videos }: { projectId: string; videos: SourceVideo[] }) {
  const clipsQuery = useQuery({
    queryKey: ["clips", projectId],
    queryFn: () => api.listClips(projectId),
    refetchInterval: 5000,
  });

  const videoById = new Map(videos.map((v) => [v.id, v]));
  const clips = (clipsQuery.data ?? []).slice().sort((a, b) => b.viral_score - a.viral_score);

  if (clipsQuery.isLoading) return <p className="text-slate-400 text-sm">Cargando clips...</p>;

  if (clips.length === 0) {
    return (
      <div className="border border-dashed border-surface-border rounded-xl p-8 text-center text-slate-500 text-sm">
        Todavia no hay clips candidatos. Importa un video y espera a que el analisis termine.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {clips.map((clip) => (
        <ClipCard key={clip.id} clip={clip} video={videoById.get(clip.source_video_id)} />
      ))}
    </div>
  );
}
