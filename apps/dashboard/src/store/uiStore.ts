import { create } from 'zustand';

interface UiStore {
  sidebarOpen: boolean;
  modal: string | null;
  toggleSidebar: () => void;
  openModal: (id: string) => void;
  closeModal: () => void;
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarOpen: true,
  modal: null,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  openModal: (id) => set({ modal: id }),
  closeModal: () => set({ modal: null }),
}));
