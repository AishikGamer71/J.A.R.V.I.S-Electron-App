import { ipcMain, app, BrowserWindow, dialog } from 'electron'

// Handlers Imports
import registerWormhole from './handlers/ai/wormhole'
import registerWebAgent from './handlers/ai/web-agent'
import registerRealityHacker from './handlers/ai/reality-hacker'
import registerPermanentMemory from './handlers/ai/permanent-memory'
import registerIpcHandlers from './handlers/ai/jarvis-memory'
import registerGhostControl from './handlers/ai/ghost-control'

import registerSecurityVault from './handlers/security/security-vault'
import registerLockSystem from './handlers/security/lock-system'

import registerSystemControl from './handlers/system/terminal-control'
import registerSystemHandlers from './handlers/system/system-info'
import registerAppLauncher from './handlers/system/app-launcher'
import registerAdbHandlers from './handlers/system/adb-manager'
import registerDropZoneControl from './handlers/system/smart-drop-zone'
import registerScreenPeeler from './handlers/system/screen-peeler'
import registerPhantomKeyboard from './handlers/system/phantom-control'
import { setupTerminal } from './handlers/system/terminal'

import registerNotesHandlers from './handlers/features/notes-manager'
import registerLocationHandlers from './handlers/features/live-location'
import registerGmailHandlers from './handlers/features/gmail-manager'
import registerGalleryHandlers from './handlers/features/gallery-manager'
import registerWidgetMaker from './handlers/features/widget-manager'
import registerTaskManager from './handlers/features/task-manager'

import registerFileWrite from './handlers/fs/file-write'
import registerFileRead from './handlers/fs/file-read'
import registerFileOps from './handlers/fs/file-ops'
import registerFileOpen from './handlers/fs/file-open'
import registerFileScanner from './handlers/fs/file-launcher'
import registerDirLoader from './handlers/fs/dir-load'

import { registerUserProfileHandlers } from './handlers/profiles/user-profile'
import { registerSystemProfileHandlers } from './handlers/profiles/system-profile'

export function registerJarvisHandlers() {
  try { registerTaskManager() } catch (e) { console.error(e) }
  try { registerWormhole({ ipcMain }) } catch (e) { console.error(e) }

  try { registerSecurityVault() } catch (e) { console.error(e) }
  try { registerLockSystem() } catch (e) { console.error(e) }

  try { registerWebAgent(ipcMain) } catch (e) { console.error(e) }
  try { registerSystemControl(ipcMain) } catch (e) { console.error(e) }
  try { registerRealityHacker(ipcMain) } catch (e) { console.error(e) }
  try { registerPermanentMemory({ ipcMain, app }) } catch (e) { console.error(e) }
  try { registerNotesHandlers(ipcMain) } catch (e) { console.error(e) }
  try { registerLocationHandlers(ipcMain) } catch (e) { console.error(e) }
  try { registerIpcHandlers({ ipcMain, app }) } catch (e) { console.error(e) }
  try { registerGmailHandlers(ipcMain) } catch (e) { console.error(e) }
  try { registerGhostControl(ipcMain) } catch (e) { console.error(e) }
  try { registerSystemHandlers(ipcMain) } catch (e) { console.error(e) }
  try { registerGalleryHandlers(ipcMain) } catch (e) { console.error(e) }
  try { registerFileWrite(ipcMain) } catch (e) { console.error(e) }
  try { registerFileRead(ipcMain) } catch (e) { console.error(e) }
  try { registerFileOps(ipcMain) } catch (e) { console.error(e) }
  try { registerFileOpen(ipcMain) } catch (e) { console.error(e) }
  try { registerFileScanner(ipcMain) } catch (e) { console.error(e) }
  try { registerDirLoader(ipcMain) } catch (e) { console.error(e) }
  try { registerAppLauncher(ipcMain) } catch (e) { console.error(e) }
  try { registerAdbHandlers(ipcMain) } catch (e) { console.error(e) }

  try { registerDropZoneControl(ipcMain) } catch (e) { console.error(e) }
  try { registerScreenPeeler() } catch (e) { console.error(e) }
  try { registerPhantomKeyboard() } catch (e) { console.error(e) }

  try { registerWidgetMaker() } catch (e) { console.error(e) }
  
  try { registerUserProfileHandlers() } catch (e) { console.error(e) }
  try { registerSystemProfileHandlers() } catch (e) { console.error(e) }


  // Working directory and dialog pickers
  ipcMain.removeHandler('dialog:openDirectory')
  ipcMain.handle('dialog:openDirectory', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openDirectory']
    })
    if (result.canceled || result.filePaths.length === 0) {
      return null
    }
    return result.filePaths[0]
  })

  ipcMain.removeHandler('window-is-maximized')
  ipcMain.handle('window-is-maximized', (event) => {
    const win = BrowserWindow.fromWebContents(event.sender)
    return win ? win.isMaximized() : false
  })

  // App version and utility handlers
  ipcMain.handle('get-app-version', async () => '1.0.0')
  ipcMain.handle('select-storage-path', async () => null)
  ipcMain.handle('check-for-updates', async () => false)
  ipcMain.handle('download-update', async () => false)
  ipcMain.handle('install-update', async () => false)

  // Sidecar & Settings handlers
  ipcMain.removeHandler('jarvis:sidecar:status')
  ipcMain.handle('jarvis:sidecar:status', async () => {
    try {
      const controller = new AbortController()
      const timer = setTimeout(() => controller.abort(), 1200)
      const res = await fetch('http://127.0.0.1:8765/health', { signal: controller.signal })
      clearTimeout(timer)
      if (res.ok) {
        const data = await res.json()
        return { running: true, port: 8765, health: data }
      }
      return { running: false, port: 8765 }
    } catch {
      return { running: false, port: 8765 }
    }
  })

  ipcMain.removeHandler('jarvis:sidecar:restart')
  ipcMain.handle('jarvis:sidecar:restart', async () => {
    try {
      const res = await fetch('http://127.0.0.1:8765/health')
      return res.ok
    } catch {
      return false
    }
  })

  ipcMain.removeHandler('jarvis:apiKey:get')
  ipcMain.handle('jarvis:apiKey:get', async (_event, provider: string) => {
    const key = provider === 'gemini' ? 'GEMINI_API_KEY' : `${provider.toUpperCase()}_API_KEY`
    return process.env[key] || null
  })

  ipcMain.removeHandler('jarvis:apiKey:save')
  ipcMain.handle('jarvis:apiKey:save', async (_event, provider: string, apiKey: string) => {
    const key = provider === 'gemini' ? 'GEMINI_API_KEY' : `${provider.toUpperCase()}_API_KEY`
    process.env[key] = apiKey
    // Also notify sidecar
    try {
      await fetch('http://127.0.0.1:8765/api/env', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value: apiKey })
      })
    } catch {}
    return true
  })

  ipcMain.removeHandler('jarvis:takeScreenshot')
  ipcMain.handle('jarvis:takeScreenshot', async () => {
    try {
      const screenshot = require('screenshot-desktop')
      const imgBuffer = await screenshot({ format: 'png' })
      return { base64: imgBuffer.toString('base64') }
    } catch (e: any) {
      return { error: e.message }
    }
  })
}

export function setupJarvisTerminal(mainWindow: BrowserWindow) {
  try { setupTerminal(mainWindow) } catch (e) { console.error(e) }
}
