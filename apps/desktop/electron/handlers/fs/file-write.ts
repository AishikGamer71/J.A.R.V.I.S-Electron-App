import { IpcMain, app } from 'electron'
import fs from 'fs/promises'
import path from 'path'

export default function registerFileWrite(ipcMain: IpcMain) {
  ipcMain.handle('write-file', async (_event, { fileName, content }) => {
    try {
      const isAbsolutePath = fileName.includes('/') || fileName.includes('\\')
      const targetPath = isAbsolutePath ? fileName : path.join(app.getPath('desktop'), fileName)

      console.log(`[audit:fs:write] ${new Date().toISOString()} Writing ${content.length} bytes to ${targetPath}`)
      await fs.writeFile(targetPath, content, 'utf-8')
      return `Success. File saved to: ${targetPath}`
    } catch (err) {
      console.error(`[audit:fs:write:error] ${new Date().toISOString()} Failed to write ${fileName}:`, err)
      return `Error writing file: ${err}`
    }
  })
}
