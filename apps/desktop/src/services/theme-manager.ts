export type ThemePresetId = 'emerald' | 'sarvam-ai' | 'midnight-frost' | 'custom'

export interface ThemePresetData {
  id: ThemePresetId
  name: string
  subtitle: string
  primaryColor: string
  secondaryColor: string
  bgColor: string
  surfaceColor: string
  borderAccent: string
  glowColor: string
  description: string
  iconBadge: string
}

export interface ThemeSettings {
  preset: ThemePresetId
  primaryColor: string
  secondaryColor: string
  bgColor: string
  surfaceColor: string
  borderAccent: string
  glowColor: string
  glassBlur: number
  glowIntensity: 'none' | 'subtle' | 'vibrant'
  hologramGrid: boolean
  particlesEnabled: boolean
  uiDensity: 'compact' | 'standard' | 'spacious'
  fontFamily: 'mono' | 'sans' | 'tech'
}

export const PRESET_THEMES: Record<Exclude<ThemePresetId, 'custom'>, ThemePresetData> = {
  emerald: {
    id: 'emerald',
    name: 'JARVIS Matrix',
    subtitle: 'Emerald Protocol (Default)',
    primaryColor: '#10b981',
    secondaryColor: '#06b6d4',
    bgColor: '#050505',
    surfaceColor: 'rgba(12, 20, 16, 0.75)',
    borderAccent: 'rgba(16, 185, 129, 0.25)',
    glowColor: 'rgba(16, 185, 129, 0.4)',
    description: 'Autonomous neural network green with cybernetic cyan secondary accents.',
    iconBadge: '⚡'
  },
  'sarvam-ai': {
    id: 'sarvam-ai',
    name: 'Sarvam AI',
    subtitle: 'Gateway Orange & Horizon Blue',
    primaryColor: '#e67e22',
    secondaryColor: '#3498db',
    bgColor: '#0a0a0f',
    surfaceColor: 'rgba(20, 14, 10, 0.75)',
    borderAccent: 'rgba(230, 126, 34, 0.25)',
    glowColor: 'rgba(230, 126, 34, 0.4)',
    description: 'Warm gateway orange with horizon blue, inspired by Sarvam AI\'s blue-to-orange brand spectrum.',
    iconBadge: '🪷'
  },
  'midnight-frost': {
    id: 'midnight-frost',
    name: 'Midnight Frost',
    subtitle: 'Frost Silver & Steel Blue',
    primaryColor: '#e2e8f0',
    secondaryColor: '#64748b',
    bgColor: '#000000',
    surfaceColor: 'rgba(15, 15, 20, 0.75)',
    borderAccent: 'rgba(226, 232, 240, 0.2)',
    glowColor: 'rgba(226, 232, 240, 0.3)',
    description: 'Icy frost silver on true black with cool steel blue accents. Clean, minimal, and elegant.',
    iconBadge: '❄️'
  }
}

export const DEFAULT_THEME_SETTINGS: ThemeSettings = {
  preset: 'emerald',
  primaryColor: PRESET_THEMES.emerald.primaryColor,
  secondaryColor: PRESET_THEMES.emerald.secondaryColor,
  bgColor: PRESET_THEMES.emerald.bgColor,
  surfaceColor: PRESET_THEMES.emerald.surfaceColor,
  borderAccent: PRESET_THEMES.emerald.borderAccent,
  glowColor: PRESET_THEMES.emerald.glowColor,
  glassBlur: 16,
  glowIntensity: 'vibrant',
  hologramGrid: true,
  particlesEnabled: true,
  uiDensity: 'standard',
  fontFamily: 'sans'
}

export function hexToRgba(hex: string, alpha: number): string {
  const cleanHex = hex.replace('#', '')
  if (cleanHex.length !== 6 && cleanHex.length !== 3) return `rgba(16, 185, 129, ${alpha})`
  const r = parseInt(cleanHex.length === 3 ? cleanHex[0] + cleanHex[0] : cleanHex.substring(0, 2), 16)
  const g = parseInt(cleanHex.length === 3 ? cleanHex[1] + cleanHex[1] : cleanHex.substring(2, 4), 16)
  const b = parseInt(cleanHex.length === 3 ? cleanHex[2] + cleanHex[2] : cleanHex.substring(4, 6), 16)
  return `rgba(${r}, ${g}, ${b}, ${alpha})`
}

export function applyThemeToDom(theme: ThemeSettings) {
  if (typeof document === 'undefined') return
  const root = document.documentElement

  const primary = theme.primaryColor || '#10b981'
  const secondary = theme.secondaryColor || '#06b6d4'
  const bg = theme.bgColor || '#050505'
  const blur = theme.glassBlur ?? 16
  const glowMultiplier = theme.glowIntensity === 'none' ? 0 : theme.glowIntensity === 'subtle' ? 0.5 : 1

  const border = hexToRgba(primary, 0.25)
  const glow = hexToRgba(primary, 0.4 * glowMultiplier)
  const surface = hexToRgba(bg === '#050505' ? '#0c1410' : bg === '#030712' ? '#0a1226' : '#141416', 0.8)

  root.style.setProperty('--theme-primary', primary)
  root.style.setProperty('--theme-primary-hover', hexToRgba(primary, 0.85))
  root.style.setProperty('--theme-secondary', secondary)
  root.style.setProperty('--theme-bg', bg)
  root.style.setProperty('--theme-surface', surface)
  root.style.setProperty('--theme-border', border)
  root.style.setProperty('--theme-glow', glow)
  root.style.setProperty('--theme-blur', `${blur}px`)

  // Apply directly to body styling
  document.body.style.backgroundColor = bg
  root.style.backgroundColor = bg
}
