import { ipcMain } from 'electron'
import si from 'systeminformation'
import { exec } from 'child_process'
import util from 'util'

const execAsync = util.promisify(exec)

export default function registerTaskManager() {
  ipcMain.handle('get-system-load', async () => {
    try {
      const [load, mem] = await Promise.all([
        si.currentLoad(),
        si.mem()
      ])
      return {
        success: true,
        cpu: load.currentLoad.toFixed(1),
        memory: ((mem.active / mem.total) * 100).toFixed(1),
        memoryUsedGb: (mem.active / 1024 / 1024 / 1024).toFixed(1),
        memoryTotalGb: (mem.total / 1024 / 1024 / 1024).toFixed(1)
      }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle('get-processes', async () => {
    try {
      const data = await si.processes()
      const processes = data.list

      // Group processes by name
      const grouped = new Map<string, any>()

      for (const p of processes) {
        // Skip idle process
        if (p.name.toLowerCase().includes('idle')) continue

        const memMb = p.memRss / 1024
        
        if (grouped.has(p.name)) {
          const group = grouped.get(p.name)
          group.cpu += p.cpu
          group.mem += memMb
          group.children.push({
            pid: p.pid,
            cpu: p.cpu,
            mem: memMb,
            user: p.user || 'System'
          })
        } else {
          grouped.set(p.name, {
            name: p.name,
            pid: p.pid, // Main PID
            cpu: p.cpu,
            mem: memMb,
            user: p.user || 'System',
            path: p.path || '',
            children: [{
              pid: p.pid,
              cpu: p.cpu,
              mem: memMb,
              user: p.user || 'System'
            }]
          })
        }
      }

      // Convert map to array and sort by memory usage descending
      const result = Array.from(grouped.values()).sort((a, b) => b.mem - a.mem)

      return { success: true, processes: result }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle('kill-process', async (_event, pid: number) => {
    try {
      // taskkill /F /T kills the process and any child processes
      await execAsync(`taskkill /PID ${pid} /F /T`)
      return { success: true }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle('get-startup-apps', async () => {
    try {
      const { stdout } = await execAsync('Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | ConvertTo-Json -Depth 1 -Compress', { shell: 'powershell.exe' })
      const apps = JSON.parse(stdout || '[]')
      return { success: true, apps: Array.isArray(apps) ? apps : [apps] }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle('get-services', async () => {
    try {
      const services = await si.services('*')
      return { success: true, services }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })

  ipcMain.handle('get-users', async () => {
    try {
      const users = await si.users()
      return { success: true, users }
    } catch (err: any) {
      return { success: false, error: err.message }
    }
  })
}
