import { useEffect, useRef, useState } from "react";
import type { CropRect } from "../api";

interface Props {
  videoUrl: string;
  rect: CropRect;
  onChange: (rect: CropRect) => void;
  label: string;
  previewTime?: number;
}

type DragMode = "move" | "resize" | null;

export default function CropEditor({ videoUrl, rect, onChange, label, previewTime = 0 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const [dragMode, setDragMode] = useState<DragMode>(null);
  const dragStart = useRef<{ x: number; y: number; rect: CropRect } | null>(null);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const setTime = () => {
      try {
        v.currentTime = previewTime;
        // Chromium a veces no pinta el frame tras un seek si el video nunca se reprodujo.
        // Un play()+pause() inmediato fuerza la decodificación del frame.
        const p = v.play();
        if (p && typeof p.then === "function") {
          p.then(() => v.pause()).catch(() => {});
        } else {
          v.pause();
        }
      } catch {
        /* ignore */
      }
    };
    if (v.readyState >= 1) setTime();
    else v.addEventListener("loadedmetadata", setTime, { once: true });
    return () => v.removeEventListener("loadedmetadata", setTime);
  }, [previewTime]);

  function clamp(v: number, min: number, max: number) {
    return Math.max(min, Math.min(max, v));
  }

  function onPointerDown(e: React.PointerEvent, mode: DragMode) {
    e.stopPropagation();
    e.preventDefault();
    (e.target as Element).setPointerCapture(e.pointerId);
    setDragMode(mode);
    dragStart.current = { x: e.clientX, y: e.clientY, rect: { ...rect } };
  }

  function onPointerMove(e: React.PointerEvent) {
    if (!dragMode || !dragStart.current || !containerRef.current) return;
    const bounds = containerRef.current.getBoundingClientRect();
    const dx = (e.clientX - dragStart.current.x) / bounds.width;
    const dy = (e.clientY - dragStart.current.y) / bounds.height;
    const start = dragStart.current.rect;

    if (dragMode === "move") {
      const x = clamp(start.x + dx, 0, 1 - start.w);
      const y = clamp(start.y + dy, 0, 1 - start.h);
      onChange({ ...start, x, y });
    } else if (dragMode === "resize") {
      const w = clamp(start.w + dx, 0.08, 1 - start.x);
      const h = clamp(start.h + dy, 0.08, 1 - start.y);
      onChange({ ...start, w, h });
    }
  }

  function onPointerUp() {
    setDragMode(null);
    dragStart.current = null;
  }

  return (
    <div>
      <label>{label}</label>
      <div
        ref={containerRef}
        className="crop-editor"
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        <video ref={videoRef} src={videoUrl} muted playsInline preload="auto" />
        <div
          className="crop-box"
          style={{
            left: `${rect.x * 100}%`,
            top: `${rect.y * 100}%`,
            width: `${rect.w * 100}%`,
            height: `${rect.h * 100}%`,
          }}
          onPointerDown={(e) => onPointerDown(e, "move")}
        >
          <div
            style={{ position: "absolute", right: -8, bottom: -8, width: 20, height: 20, cursor: "nwse-resize" }}
            onPointerDown={(e) => onPointerDown(e, "resize")}
          />
        </div>
      </div>
      <small className="hint">Arrastra el recuadro para mover, la esquina para cambiar el tamaño.</small>
    </div>
  );
}
