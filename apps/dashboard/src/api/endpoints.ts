import { api } from './client';
import type {
  Project,
  Scene,
  Shot,
  Character,
  StoryBible,
  TimelineData,
} from '../types';

// ── Projects ──
export const getProjects = () => api.get<Project[]>('/projects');
export const createProject = (data: Partial<Project>) =>
  api.post<Project>('/projects', data);
export const getProject = (id: string) => api.get<Project>(`/projects/${id}`);
export const updateProject = (id: string, data: Partial<Project>) =>
  api.patch<Project>(`/projects/${id}`, data);
export const deleteProject = (id: string) => api.delete<void>(`/projects/${id}`);
export const deleteAllProjects = () => api.delete<void>('/projects');

// ── Story ──
export const generateStory = (projectId: string, data: any) =>
  api.post<StoryBible>(`/projects/${projectId}/story/generate`, data);
export const getStory = (projectId: string) =>
  api.get<StoryBible>(`/projects/${projectId}/story`);
export const regenerateStory = (projectId: string, data: any) =>
  api.post<StoryBible>(`/projects/${projectId}/story/regenerate`, data);
export const materializeStory = (projectId: string) =>
  api.post<{ scenes: number; characters: number }>(
    `/projects/${projectId}/story/materialize`
  );

// ── Scenes ──
export const getScenes = (projectId: string, episode?: number) =>
  api.get<Scene[]>(`/projects/${projectId}/scenes${episode !== undefined ? `?episode=${episode}` : ''}`);
export const createScene = (projectId: string, data: Partial<Scene>) =>
  api.post<Scene>(`/projects/${projectId}/scenes`, data);
export const updateScene = (id: string, data: Partial<Scene>) =>
  api.patch<Scene>(`/scenes/${id}`, data);
export const deleteScene = (id: string) => api.delete<void>(`/scenes/${id}`);
export const getTimeline = (projectId: string) =>
  api.get<TimelineData>(`/projects/${projectId}/timeline`);

// ── Shots ──
export const getShots = (sceneId: string) =>
  api.get<Shot[]>(`/scenes/${sceneId}/shots`);
export const createShot = (sceneId: string, data: Partial<Shot>) =>
  api.post<Shot>(`/scenes/${sceneId}/shots`, data);
export const updateShot = (id: string, data: Partial<Shot>) =>
  api.patch<Shot>(`/shots/${id}`, data);
export const deleteShot = (id: string) => api.delete<void>(`/shots/${id}`);
export const reorderShots = (sceneId: string, shotIds: string[]) =>
  api.patch<Shot[]>(`/scenes/${sceneId}/shots/reorder`, { shot_ids: shotIds });

// ── Generation ──
export const generateBackground = (shotId: string) =>
  api.post<{ asset_id: string }>(`/shots/${shotId}/generate-background`);
export const generateKeyframe = (shotId: string) =>
  api.post<{ asset_id: string; prompt: string }>(
    `/shots/${shotId}/generate-keyframe`
  );
export const generateAllKeyframes = (sceneId: string) =>
  api.post<{ generated: number; total: number }>(
    `/scenes/${sceneId}/generate-all-keyframes`
  );
export const generateAudio = (shotId: string) =>
  api.post<{ asset_id: string }>(`/shots/${shotId}/generate-audio`);
export const generateAllAudio = (sceneId: string) =>
  api.post<{ generated: number; total: number }>(
    `/scenes/${sceneId}/generate-all-audio`
  );
export const generateLipSync = (shotId: string) =>
  api.post<{ asset_id: string }>(`/shots/${shotId}/generate-lipsync`);
export const exportScene = (sceneId: string) =>
  api.post<{ job_id: string; scene_id: string }>(`/scenes/${sceneId}/export`);
export const exportProject = (projectId: string) =>
  api.post<{ batch_id: string; concat_job_id: string; scene_count: number }>(
    `/projects/${projectId}/export`
  );
export const getAssetDownloadUrl = (assetId: string) =>
  `/api/v1/assets/${assetId}/download`;

// ── Characters ──
export const getCharacters = (projectId: string) =>
  api.get<Character[]>(`/projects/${projectId}/characters`);
export const createCharacter = (projectId: string, data: Partial<Character>) =>
  api.post<Character>(`/projects/${projectId}/characters`, data);
export const updateCharacter = (id: string, data: Partial<Character>) =>
  api.patch<Character>(`/characters/${id}`, data);
export const deleteCharacter = (id: string) => api.delete<void>(`/characters/${id}`);
export const generateCharacterImage = (id: string) =>
  api.post<{ asset_id: string; character_id: string }>(`/characters/${id}/generate-image`, {});
export const generateReferenceSheet = (characterId: string) =>
  api.post<Record<string, string>>(`/characters/${characterId}/generate-reference-sheet`);
export const generateCharacterSheet = (characterId: string) =>
  api.post<Record<string, string>>(`/characters/${characterId}/generate-character-sheet`);
export const generateOutfitSheet = (characterId: string) =>
  api.post<Record<string, string>>(`/characters/${characterId}/generate-outfit-sheet`);
export const generateAssetSheet = (characterId: string) =>
  api.post<Record<string, string>>(`/characters/${characterId}/generate-asset-sheet`);
export const generateExpressionSheet = (characterId: string, expressions?: string[]) =>
  api.post<Record<string, string>>(`/characters/${characterId}/generate-expression-sheet`, { expressions });
export const generateFullReference = (characterId: string, skip_phases?: string[]) =>
  api.post<Record<string, string>>(`/characters/${characterId}/generate-full-reference`, { skip_phases });

// ── Assets ──
export const getAssets = (projectId: string) =>
  api.get<unknown[]>(`/projects/${projectId}/assets`);

// ── Jobs ──
export const getJobs = (projectId: string) =>
  api.get<unknown[]>(`/projects/${projectId}/jobs`);
