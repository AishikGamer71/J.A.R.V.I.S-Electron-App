import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  DEFAULT_THEME_SETTINGS,
  PRESET_THEMES,
  ThemePresetId,
  ThemeSettings,
  applyThemeToDom
} from '@/services/theme-manager'

interface SettingsState {
  hiddenTabs: string[]
  voice: string
  temperature: number
  maxTokens: number
  alwaysOnTop: boolean
  autoStart: boolean
  storagePath: string
  uiSoundEffects: boolean
  computeMode: 'local' | 'cloud' | 'adaptive'
  model: string
  thinkingEnabled: boolean
  reasoningEffort: 'none' | 'low' | 'medium' | 'high'
  localEndpoint: string
  theme: ThemeSettings
  toggleTabVisibility: (tabId: string) => void
  setVoice: (voice: string) => void
  setTemperature: (temperature: number) => void
  setMaxTokens: (maxTokens: number) => void
  setAlwaysOnTop: (alwaysOnTop: boolean) => void
  setAutoStart: (autoStart: boolean) => void
  setStoragePath: (storagePath: string) => void
  setUiSoundEffects: (uiSoundEffects: boolean) => void
  setComputeMode: (mode: 'local' | 'cloud' | 'adaptive') => void
  setModel: (model: string) => void
  setThinkingEnabled: (thinkingEnabled: boolean) => void
  setReasoningEffort: (reasoningEffort: 'none' | 'low' | 'medium' | 'high') => void
  setLocalEndpoint: (endpoint: string) => void
  setTheme: (themeUpdate: Partial<ThemeSettings>) => void
  setThemePreset: (presetId: ThemePresetId) => void
  resetThemeToDefault: () => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      hiddenTabs: [],
      voice: 'Charon',
      temperature: 0.7,
      maxTokens: 2048,
      alwaysOnTop: false,
      autoStart: false,
      storagePath: '',
      uiSoundEffects: true,
      computeMode: 'adaptive',
      model: 'gemini-2.5-pro',
      thinkingEnabled: true,
      reasoningEffort: 'medium',
      localEndpoint: 'http://localhost:1234/v1',
      theme: DEFAULT_THEME_SETTINGS,
      toggleTabVisibility: (tabId) =>
        set((state) => ({
          hiddenTabs: state.hiddenTabs.includes(tabId)
            ? state.hiddenTabs.filter((id) => id !== tabId)
            : [...state.hiddenTabs, tabId]
        })),
      setVoice: (voice) => set({ voice }),
      setTemperature: (temperature) => set({ temperature }),
      setMaxTokens: (maxTokens) => set({ maxTokens }),
      setAlwaysOnTop: (alwaysOnTop) => set({ alwaysOnTop }),
      setAutoStart: (autoStart) => set({ autoStart }),
      setStoragePath: (storagePath) => set({ storagePath }),
      setUiSoundEffects: (uiSoundEffects) => set({ uiSoundEffects }),
      setComputeMode: (computeMode) => set({ computeMode }),
      setModel: (model) => set({ model }),
      setThinkingEnabled: (thinkingEnabled) => set({ thinkingEnabled }),
      setReasoningEffort: (reasoningEffort) => set({ reasoningEffort }),
      setLocalEndpoint: (localEndpoint) => set({ localEndpoint }),
      setTheme: (themeUpdate) => {
        const nextTheme = { ...get().theme, ...themeUpdate, preset: themeUpdate.preset || 'custom' as ThemePresetId }
        applyThemeToDom(nextTheme)
        set({ theme: nextTheme })
      },
      setThemePreset: (presetId) => {
        if (presetId === 'custom') {
          set((state) => ({ theme: { ...state.theme, preset: 'custom' } }))
          return
        }
        const presetData = PRESET_THEMES[presetId]
        if (!presetData) return
        const nextTheme: ThemeSettings = {
          ...get().theme,
          preset: presetId,
          primaryColor: presetData.primaryColor,
          secondaryColor: presetData.secondaryColor,
          bgColor: presetData.bgColor,
          surfaceColor: presetData.surfaceColor,
          borderAccent: presetData.borderAccent,
          glowColor: presetData.glowColor
        }
        applyThemeToDom(nextTheme)
        set({ theme: nextTheme })
      },
      resetThemeToDefault: () => {
        applyThemeToDom(DEFAULT_THEME_SETTINGS)
        set({ theme: DEFAULT_THEME_SETTINGS })
      }
    }),
    {
      name: 'jarvis-settings-storage',
      onRehydrateStorage: () => (state) => {
        if (state?.theme) {
          applyThemeToDom(state.theme)
        }
      }
    }
  )
)
