import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../services/api";

const PLATFORMS = ["tiktok", "reels", "shorts", "facebook"];

export default function ProjectsPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState("");
  const [game, setGame] = useState("");
  const [platform, setPlatform] = useState("tiktok");

  const projectsQuery = useQuery({ queryKey: ["projects"], queryFn: api.listProjects });

  const createMutation = useMutation({
    mutationFn: () => api.createProject({ name, game_or_category: game || undefined, target_platform: platform }),
    onSuccess: (project) => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      setShowForm(false);
      setName("");
      setGame("");
      navigate(`/projects/${project.id}`);
    },
  });

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Proyectos</h1>
          <p className="text-slate-400 text-sm">Tus streams importados y clips generados con IA.</p>
        </div>
        <button
          className="bg-accent hover:bg-accent-hover transition-colors px-4 py-2 rounded-lg font-medium"
          onClick={() => setShowForm((v) => !v)}
        >
          + Nuevo proyecto
        </button>
      </div>

      {showForm && (
        <form
          className="bg-surface-raised border border-surface-border rounded-xl p-4 mb-6 flex flex-wrap gap-3 items-end"
          onSubmit={(e) => {
            e.preventDefault();
            if (name.trim()) createMutation.mutate();
          }}
        >
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Nombre del proyecto</label>
            <input
              autoFocus
              className="bg-surface border border-surface-border rounded px-3 py-2 w-64"
              placeholder="Ej. Warzone - Sesion viernes"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Juego / categoria</label>
            <input
              className="bg-surface border border-surface-border rounded px-3 py-2 w-48"
              placeholder="warzone, valorant..."
              value={game}
              onChange={(e) => setGame(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">Plataforma destino</label>
            <select
              className="bg-surface border border-surface-border rounded px-3 py-2"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              {PLATFORMS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
          <button
            type="submit"
            disabled={!name.trim() || createMutation.isPending}
            className="bg-accent hover:bg-accent-hover disabled:opacity-50 transition-colors px-4 py-2 rounded-lg font-medium"
          >
            {createMutation.isPending ? "Creando..." : "Crear"}
          </button>
        </form>
      )}

      {projectsQuery.isLoading && <p className="text-slate-400">Cargando proyectos...</p>}

      {projectsQuery.data && projectsQuery.data.length === 0 && (
        <div className="border border-dashed border-surface-border rounded-xl p-12 text-center text-slate-400">
          Aun no tienes proyectos. Crea uno para empezar a importar tus streams.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {projectsQuery.data?.map((project) => (
          <button
            key={project.id}
            onClick={() => navigate(`/projects/${project.id}`)}
            className="text-left bg-surface-raised border border-surface-border rounded-xl p-4 hover:border-accent transition-colors"
          >
            <h2 className="font-semibold text-lg mb-1">{project.name}</h2>
            <p className="text-slate-400 text-sm mb-3">
              {project.game_or_category || "Sin categoria"} · {project.target_platform}
            </p>
            <div className="flex gap-4 text-xs text-slate-500">
              <span>{project.video_count} videos</span>
              <span>{project.clip_count} clips</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
