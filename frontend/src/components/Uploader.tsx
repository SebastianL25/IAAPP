import { useRef, useState } from "react";
import { api } from "../api";

interface Props {
  onUploaded: (info: { video_id: string; filename: string; duration: number; width: number; height: number }) => void;
}

export default function Uploader({ onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  async function handleFile(file: File) {
    setError(null);
    setFileName(file.name);
    setProgress(0);
    try {
      const info = await api.upload(file, setProgress);
      setProgress(100);
      onUploaded(info);
    } catch (e) {
      setError((e as Error).message);
      setProgress(null);
    }
  }

  return (
    <div>
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const f = e.dataTransfer.files?.[0];
          if (f) handleFile(f);
        }}
        onClick={() => inputRef.current?.click()}
        style={{
          border: "2px dashed var(--border)",
          borderRadius: 14,
          padding: "40px 20px",
          textAlign: "center",
          cursor: "pointer",
          color: "var(--text-dim)",
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".mp4,.mkv,.mov,.webm,.avi"
          style={{ display: "none" }}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
        <div style={{ fontSize: 15, color: "var(--text)", marginBottom: 6 }}>
          Arrastra tu video aquí o haz clic para seleccionarlo
        </div>
        <div style={{ fontSize: 13 }}>MP4, MKV, MOV, WEBM o AVI</div>
      </div>
      {fileName && (
        <div style={{ marginTop: 12 }}>
          <div style={{ fontSize: 13, marginBottom: 6 }}>{fileName}</div>
          {progress != null && (
            <div className="progress-bar">
              <div style={{ width: `${progress}%` }} />
            </div>
          )}
        </div>
      )}
      {error && <div className="error-box" style={{ marginTop: 12 }}>{error}</div>}
    </div>
  );
}
