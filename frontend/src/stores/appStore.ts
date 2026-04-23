import { create } from 'zustand'
import type { Section } from '../types'

interface AppState {
  activeSection: Section
  theme: 'dark' | 'light'
  sidebarCollapsed: boolean
  refreshKey: number
  setSection: (s: Section) => void
  toggleTheme: () => void
  toggleSidebar: () => void
  triggerRefresh: () => void
}

export const useAppStore = create<AppState>((set) => ({
  activeSection: 'trade-desk',
  theme: 'dark',
  sidebarCollapsed: false,
  refreshKey: 0,
  setSection: (s) => set({ activeSection: s }),
  toggleTheme: () =>
    set((state) => {
      const next = state.theme === 'dark' ? 'light' : 'dark'
      document.documentElement.classList.toggle('theme-light', next === 'light')
      return { theme: next }
    }),
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  triggerRefresh: () => set((state) => ({ refreshKey: state.refreshKey + 1 })),
}))
