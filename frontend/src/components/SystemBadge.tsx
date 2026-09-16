import { useEffect, useState } from "react";
import { api, SystemStatus } from "../api";

export default function SystemBadge() {
  const [status, setStatus] = useState<SystemStatus | null>(null);

  useEffect(() => {
    let alive = true;
    const load = () => api.systemStatus().then((s) => alive && setStatus(s)).catch(() => {});
    load();
    const t = setInterval(load, 15000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  if (!status) return null;

  return (
    <div className="system-badge">
      <span className={`pill ${status.ffmpeg_ok ? "ok" : "bad"}`}>
        {status.ffmpeg_ok ? "FFmpeg listo" : "FFmpeg no encontrado"}
      </span>
      <span className={`pill ${status.gpu.active_device === "cuda" ? "ok" : ""}`}>{status.gpu.label}</span>
      <span className="pill">Modelo: {status.whisper_model}</span>
    </div>
  );
}
