import { create } from 'zustand';
import type { Project } from '../types';

interface ProjectState {
  projects: Project[];
  activeId: string | null;
  setProjects: (projects: Project[]) => void;
  setActive: (id: string) => void;
  addProject: (p: Project) => void;
  updateProject: (id: string, p: Partial<Project>) => void;
  removeProject: (id: string) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  activeId: null,
  setProjects: (projects) => set({ projects }),
  setActive: (id) => set({ activeId: id }),
  addProject: (p) => set((s) => ({ projects: [...s.projects, p] })),
  updateProject: (id, p) =>
    set((s) => ({
      projects: s.projects.map((x) => (x.id === id ? { ...x, ...p } : x)),
    })),
  removeProject: (id) =>
    set((s) => ({
      projects: s.projects.filter((x) => x.id !== id),
      activeId: s.activeId === id ? null : s.activeId,
    })),
}));
