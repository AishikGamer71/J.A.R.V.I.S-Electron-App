import fs from 'fs'
import path from 'path'
import { IpcMain, App } from 'electron'

export default function registerIpcHandlers({ ipcMain, app }: { ipcMain: IpcMain; app: App }) {
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
  const storageDir = isDev 
    ? path.resolve(process.cwd(), 'storage') 
    : path.join(app.getPath('userData'), 'storage')

  const CHAT_DIR = storageDir
  const OLD_FILE_PATH_APP = path.join(app.getPath('userData'), 'Chat', 'jarvis_memory.json')
  const OLD_IRIS_PATH_APP = path.join(app.getPath('userData'), 'Chat', 'iris_memory.json')
  const FILE_PATH = path.join(CHAT_DIR, 'jarvis_memory.json')

  if (!fs.existsSync(CHAT_DIR)) fs.mkdirSync(CHAT_DIR, { recursive: true })

  if (!fs.existsSync(FILE_PATH)) {
    if (fs.existsSync(OLD_FILE_PATH_APP)) {
      try { fs.copyFileSync(OLD_FILE_PATH_APP, FILE_PATH) } catch (e) {}
    } else if (fs.existsSync(OLD_IRIS_PATH_APP)) {
      try { fs.copyFileSync(OLD_IRIS_PATH_APP, FILE_PATH) } catch (e) {}
    }
  }

  ipcMain.removeHandler('add-message')
  ipcMain.removeHandler('get-history')

  ipcMain.handle('add-message', async (_event, msg) => {
    try {
      if (!fs.existsSync(CHAT_DIR)) fs.mkdirSync(CHAT_DIR, { recursive: true })

      let history: { role: string; content: string; timestamp: string }[] = []
      if (fs.existsSync(FILE_PATH)) {
        const data = fs.readFileSync(FILE_PATH, 'utf-8')
        history = data ? JSON.parse(data) : []
      }

      const newEntry: { role: string; content: string; timestamp: string } = {
        role: msg.role,
        content: msg.parts[0].text,
        timestamp: new Date().toISOString()
      }
      history.push(newEntry)

      if (history.length > 20) history = history.slice(-20)

      fs.writeFileSync(FILE_PATH, JSON.stringify(history, null, 2))
      return true
    } catch (err) {
      return false
    }
  })

  ipcMain.handle('get-history', async () => {
    try {
      if (fs.existsSync(FILE_PATH)) {
        const data = fs.readFileSync(FILE_PATH, 'utf-8')
        const raw = JSON.parse(data)
        return raw.map((m: any) => ({
          role: (m.role === 'iris' || m.role === 'jarvis') ? 'model' : m.role,
          parts: [{ text: m.content }]
        }))
      }
    } catch (err) {}
    return []
  })

  ipcMain.handle('clear-history', async () => {
    try {
      fs.writeFileSync(FILE_PATH, JSON.stringify([], null, 2))
      return true
    } catch (err) {
      return false
    }
  })
}
