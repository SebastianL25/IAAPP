import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { api, ApiError } from "../../services/api";

const ACCEPTED_EXTENSIONS = [".mp4", ".mov", ".mkv", ".avi", ".webm", ".ts"];

function isVideoFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export default function Importer({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [pathValue, setPathValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["videos", projectId] });
    queryClient.invalidateQueries({ queryKey: ["jobs", projectId] });
    queryClient.invalidateQueries({ queryKey: ["projects"] });
  };

  const uploadMutation = useMutation({
    mutationFn: (files: File[]) => api.importFiles(projectId, files),
    onSuccess: invalidate,
    onError: (err: unknown) => setError(err instanceof ApiError ? err.message : "Error al importar"),
  });

  const pathMutation = useMutation({
    mutationFn: (path: string) => api.importByPath(projectId, path),
    onSuccess: () => {
      invalidate();
      setPathValue("");
    },
    onError: (err: unknown) => setError(err instanceof ApiError ? err.message : "Error al importar por ruta"),
  });

  const folderMutation = useMutation({
    mutationFn: (path: string) => api.importFolder(projectId, path),
    onSuccess: () => {
      invalidate();
      setPathValue("");
    },
    onError: (err: unknown) => setError(err instanceof ApiError ? err.message : "Error al importar carpeta"),
  });

  function handleFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList).filter(isVideoFile);
    if (files.length === 0) {
      setError("Ningun archivo tiene una extension soportada (mp4, mov, mkv, avi, webm, ts)");
      return;
    }
    setError(null);
    uploadMutation.mutate(files);
  }

  const isBusy = uploadMutation.isPending || pathMutation.isPending || folderMutation.isPending;

  return (
    <div className="bg-surface-raised border border-surface-border rounded-xl p-4">
      <h3 className="font-medium mb-3">Importar videos</h3>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer ${
          dragOver ? "border-accent bg-accent/10" : "border-surface-border"
        }`}
        onClick={() => fileInputRef.current?.click()}
      >
        <p className="text-slate-300">Arrastra tus videos aqui o haz clic para seleccionar</p>
        <p className="text-xs text-slate-500 mt-1">MP4, MOV, MKV, AVI, WEBM, TS</p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS.join(",")}
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        <button
          className="text-sm bg-surface border border-surface-border rounded px-3 py-1.5 hover:border-accent"
          onClick={() => folderInputRef.current?.click()}
        >
          Seleccionar carpeta
        </button>
        <input
          ref={folderInputRef}
          type="file"
          className="hidden"
          // @ts-expect-error atributo no estandar, soportado por navegadores basados en Chromium
          webkitdirectory="true"
          multiple
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 bg-surface border border-surface-border rounded px-3 py-2 text-sm"
          placeholder="Ruta local absoluta (archivo o carpeta), ej. C:\Videos\stream.mp4"
          value={pathValue}
          onChange={(e) => setPathValue(e.target.value)}
        />
        <button
          disabled={!pathValue.trim() || isBusy}
          className="text-sm bg-surface border border-surface-border rounded px-3 py-2 hover:border-accent disabled:opacity-40"
          onClick={() => pathMutation.mutate(pathValue.trim())}
        >
          Importar archivo
        </button>
        <button
          disabled={!pathValue.trim() || isBusy}
          className="text-sm bg-surface border border-surface-border rounded px-3 py-2 hover:border-accent disabled:opacity-40"
          onClick={() => folderMutation.mutate(pathValue.trim())}
        >
          Importar carpeta
        </button>
      </div>

      {isBusy && <p className="text-xs text-accent mt-2">Importando y analizando...</p>}
      {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
    </div>
  );
}
