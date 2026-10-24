import { app, ipcMain, BrowserWindow } from 'electron'
import * as pty from 'node-pty'
import os from 'os'

export function setupTerminal(mainWindow: BrowserWindow) {
  const ptyProcesses: Record<string, pty.IPty> = {};

  function spawnShell(tabId: string, shellName: string) {
    if (ptyProcesses[tabId]) {
      try {
        ptyProcesses[tabId].kill()
      } catch (e) {}
    }
    
    const ptyProcess = pty.spawn(shellName, [], {
      name: 'xterm-color',
      cols: 80,
      rows: 30,
      cwd: process.env.USERPROFILE || process.env.HOME,
      env: process.env as Record<string, string>
    })

    ptyProcess.onData((data: any) => {
      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send('terminal-output', { tabId, data })
      }
    })
    
    ptyProcesses[tabId] = ptyProcess
  }

  // Listen for shell spawn from frontend
  ipcMain.on('terminal-spawn', (event, { tabId, shellName }) => {
    spawnShell(tabId, shellName)
  })

  // Listen for close from frontend
  ipcMain.on('terminal-close', (event, tabId) => {
    if (ptyProcesses[tabId]) {
      try { ptyProcesses[tabId].kill() } catch (e) {}
      delete ptyProcesses[tabId]
    }
  })

  // Listen for input from the renderer and write to the PTY
  ipcMain.on('terminal-input', (event, { tabId, data }) => {
    if (ptyProcesses[tabId]) ptyProcesses[tabId].write(data)
  })

  // Handle resizing from the frontend
  ipcMain.on('terminal-resize', (event, { tabId, cols, rows }) => {
    try {
      if (ptyProcesses[tabId]) ptyProcesses[tabId].resize(cols, rows)
    } catch (err) {
      console.error(`Failed to resize terminal ${tabId}:`, err)
    }
  })

  // Cleanup on exit
  app.on('before-quit', () => {
    for (const key in ptyProcesses) {
      try { ptyProcesses[key].kill() } catch (e) {}
    }
  })
}
