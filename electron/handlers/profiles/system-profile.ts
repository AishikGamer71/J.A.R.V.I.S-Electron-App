import { ipcMain, app } from 'electron'
import { IPC_CHANNELS } from '../../shared/ipc-channels'
import { SystemProfile, DEFAULT_SYSTEM_PROFILE } from '../../shared/types/profiles'
import fs from 'fs'
import path from 'path'

// Get the root directory of the project (or app data in production)
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
const storageDir = isDev 
  ? path.resolve(process.cwd(), 'storage') 
  : path.join(app.getPath('userData'), 'storage')

const SYSTEM_FILE_PATH = path.join(storageDir, 'system-profile.json')

function ensureStorageDir() {
  if (!fs.existsSync(storageDir)) {
    fs.mkdirSync(storageDir, { recursive: true })
  }
}

function readSystemProfile(): SystemProfile {
  try {
    ensureStorageDir()
    if (!fs.existsSync(SYSTEM_FILE_PATH)) {
      // By default, system storage path should default to something sensible
      const defaultProfile = { 
        ...DEFAULT_SYSTEM_PROFILE, 
        storagePath: isDev ? path.resolve(process.cwd(), 'jarvis_data') : app.getPath('userData') 
      }
      fs.writeFileSync(SYSTEM_FILE_PATH, JSON.stringify(defaultProfile, null, 2))
      return defaultProfile
    }
    const rawData = fs.readFileSync(SYSTEM_FILE_PATH, 'utf8')
    return { ...DEFAULT_SYSTEM_PROFILE, ...JSON.parse(rawData) }
  } catch (error) {
    console.error('Failed to read system profile:', error)
    return DEFAULT_SYSTEM_PROFILE
  }
}

function writeSystemProfile(data: Partial<SystemProfile>): SystemProfile {
  try {
    const current = readSystemProfile()
    const updated = { ...current, ...data }
    ensureStorageDir()
    fs.writeFileSync(SYSTEM_FILE_PATH, JSON.stringify(updated, null, 2))
    return updated
  } catch (error) {
    console.error('Failed to write system profile:', error)
    return DEFAULT_SYSTEM_PROFILE
  }
}

export function registerSystemProfileHandlers(): void {
  ipcMain.handle(IPC_CHANNELS.GET_SYSTEM_PROFILE, () => {
    return readSystemProfile()
  })

  ipcMain.handle(IPC_CHANNELS.SAVE_SYSTEM_PROFILE, (_, data: Partial<SystemProfile>) => {
    return writeSystemProfile(data)
  })
}
