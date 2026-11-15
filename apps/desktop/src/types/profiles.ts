export interface UserProfile {
  name: string
  aliases: string[]
  homeLocation: string
  preferences: Record<string, string>
}

export interface SystemProfile {
  machineName: string
  autoStart: boolean
  alwaysOnTop: boolean
  storagePath: string
  uiSoundEffects: boolean
}

export const DEFAULT_USER_PROFILE: UserProfile = {
  name: 'Commander',
  aliases: [],
  homeLocation: 'Earth',
  preferences: {}
}

export const DEFAULT_SYSTEM_PROFILE: SystemProfile = {
  machineName: 'JARVIS-MAIN',
  autoStart: false,
  alwaysOnTop: false,
  storagePath: '',
  uiSoundEffects: true
}
