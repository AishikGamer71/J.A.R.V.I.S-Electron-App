import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type WorkspaceMode = 'chat' | 'code' | 'cowork'

interface WorkspaceState {
  activeMode: WorkspaceMode
  setActiveMode: (mode: WorkspaceMode) => void
  // Code workspace state
  projectPath: string | null
  setProjectPath: (path: string | null) => void
  isFileExplorerOpen: boolean
  toggleFileExplorer: () => void
  isTerminalOpen: boolean
  toggleTerminal: () => void
  // Cowork state
  isActivityPanelOpen: boolean
  toggleActivityPanel: () => void
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      activeMode: 'chat',
      setActiveMode: (activeMode) => set({ activeMode }),
      projectPath: null,
      setProjectPath: (projectPath) => set({ projectPath }),
      isFileExplorerOpen: true,
      toggleFileExplorer: () =>
        set((state) => ({ isFileExplorerOpen: !state.isFileExplorerOpen })),
      isTerminalOpen: true,
      toggleTerminal: () =>
        set((state) => ({ isTerminalOpen: !state.isTerminalOpen })),
      isActivityPanelOpen: true,
      toggleActivityPanel: () =>
        set((state) => ({ isActivityPanelOpen: !state.isActivityPanelOpen }))
    }),
    {
      name: 'jarvis-workspace-storage'
    }
  )
)
