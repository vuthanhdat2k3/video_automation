export interface Project {
  id: string;
  name: string;
  style: string;
  aspect_ratio: string;
  story_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface Scene {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  duration_seconds: number | null;
  order_index: number;
  episode_number: number | null;
  continuity_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CameraConfig {
  angle: string;
  framing: string;
  movement: string;
  lens: string | null;
}

export interface MotionConfig {
  animation_style: string;
  easing: string;
  fps: number;
}

export interface AudioConfig {
  voice_profile: string | null;
  background_music: string | null;
  sound_effects: string[];
  volume: number;
}

export interface Shot {
  id: string;
  scene_id: string;
  order_index: number;
  duration_seconds: number;
  description: string | null;
  shot_type: string;
  camera: CameraConfig;
  motion: MotionConfig;
  audio: AudioConfig;
  background_asset_id: string | null;
  keyframe_asset_id: string | null;
  audio_asset_id: string | null;
  video_export_id: string | null;
  generation_prompt: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Character {
  id: string;
  project_id: string;
  name: string;
  role: string;
  description: string | null;
  prompt: string | null;
  asset_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Asset {
  id: string;
  project_id: string;
  type: string;
  filename: string;
  path: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface Job {
  id: string;
  project_id: string;
  job_type: string;
  status: string;
  progress: number;
  input_data: Record<string, unknown> | null;
  result_data: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface StoryBible {
  series_name: string;
  series_overview: string;
  target_audience: string;
  total_episodes: number;
  episode_duration_minutes: number;
  genre: string[];
  themes: string[];
  key_locations: string[];
  characters: StoryCharacter[];
  episodes: Episode[];
  continuity_notes: string;
}

export interface StoryCharacter {
  name: string;
  role: string;
  personality: string;
  backstory: string;
  arc: string;
}

export interface Episode {
  number: number;
  title: string;
  summary: string;
  scenes: EpisodeScene[];
}

export interface EpisodeScene {
  number: number;
  title: string;
  summary: string;
  characters: string[];
  setting: string;
  duration_seconds: number;
}

export interface ApiResponse<T> {
  data: T;
  error: string | null;
}

export interface TimelineItem {
  scene: Scene;
  shots: Shot[];
}
