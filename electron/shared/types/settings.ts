/**
 * Settings types shared between Main process and Renderer.
 */

export interface SettingsData {
  hiddenTabs: string[]
  voice: string
  temperature: number
  maxTokens: number
  alwaysOnTop: boolean
  autoStart: boolean
  storagePath: string
  uiSoundEffects: boolean
}
