import { IPC_CHANNELS } from '@/types/ipc-channels'
import { UserProfile, SystemProfile, DEFAULT_USER_PROFILE, DEFAULT_SYSTEM_PROFILE } from '@/types/profiles'

const getIpc = () => (window as any).electron?.ipcRenderer

export const profileApi = {
  // User Profile
  async getUserProfile(): Promise<UserProfile> {
    const ipc = getIpc()
    if (!ipc) {
      const stored = localStorage.getItem('jarvis_user_profile')
      return stored ? JSON.parse(stored) : DEFAULT_USER_PROFILE
    }
    try {
      return await ipc.invoke(IPC_CHANNELS.GET_USER_PROFILE)
    } catch {
      return DEFAULT_USER_PROFILE
    }
  },
  
  async saveUserProfile(data: Partial<UserProfile>): Promise<UserProfile> {
    const ipc = getIpc()
    if (!ipc) {
      const current = await this.getUserProfile()
      const updated = { ...current, ...data }
      localStorage.setItem('jarvis_user_profile', JSON.stringify(updated))
      return updated
    }
    return ipc.invoke(IPC_CHANNELS.SAVE_USER_PROFILE, data)
  },

  // System Profile
  async getSystemProfile(): Promise<SystemProfile> {
    const ipc = getIpc()
    if (!ipc) {
      const stored = localStorage.getItem('jarvis_system_profile')
      return stored ? JSON.parse(stored) : DEFAULT_SYSTEM_PROFILE
    }
    try {
      return await ipc.invoke(IPC_CHANNELS.GET_SYSTEM_PROFILE)
    } catch {
      return DEFAULT_SYSTEM_PROFILE
    }
  },

  async saveSystemProfile(data: Partial<SystemProfile>): Promise<SystemProfile> {
    const ipc = getIpc()
    if (!ipc) {
      const current = await this.getSystemProfile()
      const updated = { ...current, ...data }
      localStorage.setItem('jarvis_system_profile', JSON.stringify(updated))
      return updated
    }
    return ipc.invoke(IPC_CHANNELS.SAVE_SYSTEM_PROFILE, data)
  }
}
