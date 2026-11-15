import { create } from 'zustand'
import { UserProfile, SystemProfile, DEFAULT_USER_PROFILE, DEFAULT_SYSTEM_PROFILE } from '@/types/profiles'
import { profileApi } from '../api/data/profile-api'

interface ProfileState {
  user: UserProfile
  system: SystemProfile
  isLoading: boolean
  
  // Actions
  loadProfiles: () => Promise<void>
  updateUser: (data: Partial<UserProfile>) => Promise<void>
  updateSystem: (data: Partial<SystemProfile>) => Promise<void>
}

export const useProfileStore = create<ProfileState>((set) => ({
  user: DEFAULT_USER_PROFILE,
  system: DEFAULT_SYSTEM_PROFILE,
  isLoading: true,

  loadProfiles: async () => {
    set({ isLoading: true })
    try {
      const user = await profileApi.getUserProfile()
      const system = await profileApi.getSystemProfile()
      set({ user, system, isLoading: false })
    } catch (error) {
      console.error('Failed to load profiles:', error)
      set({ isLoading: false })
    }
  },

  updateUser: async (data: Partial<UserProfile>) => {
    try {
      const updatedUser = await profileApi.saveUserProfile(data)
      set({ user: updatedUser })
    } catch (error) {
      console.error('Failed to update user profile:', error)
    }
  },

  updateSystem: async (data: Partial<SystemProfile>) => {
    try {
      const updatedSystem = await profileApi.saveSystemProfile(data)
      set({ system: updatedSystem })
    } catch (error) {
      console.error('Failed to update system profile:', error)
    }
  }
}))
