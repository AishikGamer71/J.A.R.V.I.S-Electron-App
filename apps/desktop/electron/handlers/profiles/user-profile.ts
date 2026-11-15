import { ipcMain, app } from 'electron'
import { IPC_CHANNELS } from '../../shared/ipc-channels'
import { UserProfile, DEFAULT_USER_PROFILE } from '../../shared/types/profiles'
import fs from 'fs'
import path from 'path'

// Get the root directory of the project (or app data in production)
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
const storageDir = isDev 
  ? path.resolve(process.cwd(), 'storage') 
  : path.join(app.getPath('userData'), 'storage')

const USER_FILE_PATH = path.join(storageDir, 'user-profile.json')

function ensureStorageDir() {
  if (!fs.existsSync(storageDir)) {
    fs.mkdirSync(storageDir, { recursive: true })
  }
}

function readUserProfile(): UserProfile {
  try {
    ensureStorageDir()
    if (!fs.existsSync(USER_FILE_PATH)) {
      fs.writeFileSync(USER_FILE_PATH, JSON.stringify(DEFAULT_USER_PROFILE, null, 2))
      return DEFAULT_USER_PROFILE
    }
    const rawData = fs.readFileSync(USER_FILE_PATH, 'utf8')
    return { ...DEFAULT_USER_PROFILE, ...JSON.parse(rawData) }
  } catch (error) {
    console.error('Failed to read user profile:', error)
    return DEFAULT_USER_PROFILE
  }
}

function writeUserProfile(data: Partial<UserProfile>): UserProfile {
  try {
    const current = readUserProfile()
    const updated = { ...current, ...data }
    ensureStorageDir()
    fs.writeFileSync(USER_FILE_PATH, JSON.stringify(updated, null, 2))
    return updated
  } catch (error) {
    console.error('Failed to write user profile:', error)
    return DEFAULT_USER_PROFILE
  }
}

export function registerUserProfileHandlers(): void {
  ipcMain.handle(IPC_CHANNELS.GET_USER_PROFILE, () => {
    return readUserProfile()
  })

  ipcMain.handle(IPC_CHANNELS.SAVE_USER_PROFILE, (_, data: Partial<UserProfile>) => {
    return writeUserProfile(data)
  })
}
