import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import VideoCard from "../components/VideoCard";
import ClipList from "../features/clip-review/ClipList";
import Importer from "../features/importer/Importer";
import ProcessingQueuePanel from "../features/processing-queue/ProcessingQueuePanel";
import { useProjectSocket } from "../hooks/useProjectSocket";
import { api } from "../services/api";

export default function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  useProjectSocket(projectId);

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.getProject(projectId as string),
    enabled: !!projectId,
  });

  const videosQuery = useQuery({
    queryKey: ["videos", projectId],
    queryFn: () => api.listVideosByProject(projectId as string),
    enabled: !!projectId,
    refetchInterval: 5000,
  });

  if (!projectId) return null;

  return (
    <div className="max-w-6xl mx-auto p-6 flex flex-col gap-6">
      <div>
        <Link to="/" className="text-xs text-slate-500 hover:text-accent">
          ← Proyectos
        </Link>
        <h1 className="text-2xl font-semibold mt-1">{projectQuery.data?.name ?? "Cargando..."}</h1>
        <p className="text-slate-400 text-sm">
          {projectQuery.data?.game_or_category || "Sin categoria"} · destino {projectQuery.data?.target_platform}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <Importer projectId={projectId} />
        </div>
        <ProcessingQueuePanel projectId={projectId} />
      </div>

      <div>
        <h2 className="font-medium mb-3">Videos importados ({videosQuery.data?.length ?? 0})</h2>
        {videosQuery.data && videosQuery.data.length === 0 && (
          <p className="text-sm text-slate-500">Aun no importas videos en este proyecto.</p>
        )}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {videosQuery.data?.map((video) => (
            <VideoCard key={video.id} video={video} projectId={projectId} />
          ))}
        </div>
      </div>

      <div>
        <h2 className="font-medium mb-3">Clips candidatos</h2>
        <ClipList projectId={projectId} videos={videosQuery.data ?? []} />
      </div>
    </div>
  );
}
