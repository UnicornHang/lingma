import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface CurrentWorkState {
  /** 当前正在创作的作品 id；侧栏设定入口与作品卡都读它 */
  currentWorkId: string | null;
  setCurrentWorkId: (id: string | null) => void;
}

export const useCurrentWorkStore = create<CurrentWorkState>()(
  persist(
    (set) => ({
      currentWorkId: null,
      setCurrentWorkId: (id) => set({ currentWorkId: id }),
    }),
    { name: 'zhimeng-current-work' },
  ),
);
