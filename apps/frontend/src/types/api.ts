export interface Project {
  id: string;
  name: string;
  game_or_category: string | null;
  target_platform: string;
  language: string;
  ai_settings: Record<string, unknown>;
  status: string;
  created_at: string;
  updated_at: string;
  video_count: number;
  clip_count: number;
}

export interface VideoMetadata {
  duration_seconds: number;
  width: number;
  height: number;
  fps: number;
  video_codec: string | null;
  audio_codec: string | null;
  bitrate: number;
  audio_channels: number;
}

export interface SourceVideo {
  id: string;
  project_id: string;
  original_filename: string;
  file_hash: string;
  size_bytes: number;
  import_status: "pending" | "importing" | "ready" | "error" | "duplicate";
  error_message: string | null;
  created_at: string;
  video_metadata: VideoMetadata | null;
  has_proxy: boolean;
  has_thumbnail: boolean;
}

export interface DetectedEvent {
  id: string;
  event_type: string;
  start_time: number;
  end_time: number;
  confidence: number;
  metadata_json: Record<string, unknown>;
  source: string;
}

export interface TranscriptSegment {
  id: string;
  start_time: number;
  end_time: number;
  text: string;
}

export interface Transcript {
  id: string;
  language: string | null;
  status: string;
  full_text: string;
  segments: TranscriptSegment[];
}

export interface VideoAnalysis {
  video: SourceVideo;
  transcript: Transcript | null;
  events: DetectedEvent[];
  clip_count: number;
}

export interface ClipCandidate {
  id: string;
  project_id: string;
  source_video_id: string;
  start_time: number;
  end_time: number;
  viral_score: number;
  category: string;
  detected_events: string[];
  hook: string | null;
  reason: string;
  confidence: number;
  title: string | null;
  status: "candidate" | "approved" | "discarded";
  created_at: string;
}

export interface ProcessingJob {
  id: string;
  project_id: string | null;
  source_video_id: string | null;
  job_type: string;
  status: "pending" | "running" | "paused" | "done" | "error" | "cancelled";
  progress_percent: number;
  stage_message: string;
  error_message: string | null;
  created_at: string;
}

export interface ExportJob {
  id: string;
  clip_version_id: string;
  preset: string;
  resolution: string;
  fps: number;
  status: "queued" | "running" | "done" | "error" | "cancelled";
  progress_percent: number;
  output_path: string | null;
  error_message: string | null;
}

export interface JobProgressMessage {
  type: "job_progress" | "export_progress";
  job_id: string;
  job_type?: string;
  status: string;
  progress_percent: number;
  stage_message?: string;
}
