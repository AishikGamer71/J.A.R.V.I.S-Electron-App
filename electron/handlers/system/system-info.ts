import { IpcMain } from 'electron'
import os from 'os'
import { exec } from 'child_process'
import si from 'systeminformation'

const runCommand = (cmd: string): Promise<string> => {
  return new Promise((resolve) => {
    exec(cmd, { maxBuffer: 1024 * 1024 * 10 }, (error, stdout) => {
      if (error) {
      }
      resolve(stdout ? stdout.trim() : '')
    })
  })
}

let cpuLastSnapshot = os.cpus()

function getSystemCpuUsage() {
  const cpus = os.cpus()
  let idle = 0
  let total = 0
  for (let i = 0; i < cpus.length; i++) {
    const cpu = cpus[i]
    const prevCpu = cpuLastSnapshot[i]
    let currentTotal = 0
    for (const type in cpu.times) currentTotal += cpu.times[type]
    let prevTotal = 0
    for (const type in prevCpu.times) prevTotal += prevCpu.times[type]
    idle += cpu.times.idle - prevCpu.times.idle
    total += currentTotal - prevTotal
  }
  cpuLastSnapshot = cpus
  return total === 0 ? '0.0' : (((total - idle) / total) * 100).toFixed(1)
}

export default function registerSystemHandlers(ipcMain: IpcMain) {

  ipcMain.removeHandler('get-installed-apps')
  ipcMain.handle('get-installed-apps', async () => {
    try {
      if (os.platform() !== 'win32') return []

      const cmd = `powershell "Get-StartApps | Select-Object Name, AppID | ConvertTo-Json -Depth 1"`

      const jsonOutput = await runCommand(cmd)

      if (!jsonOutput) return []

      let rawData
      try {
        rawData = JSON.parse(jsonOutput)
      } catch (parseError) {
        return []
      }

      const appsArray = Array.isArray(rawData) ? rawData : [rawData]

      return appsArray
        .filter((a: any) => a && a.Name && a.AppID) 
        .map((a: any) => ({
          name: a.Name.trim(),
          id: a.AppID.trim()
        }))
        .sort((a, b) => a.name.localeCompare(b.name)) 
    } catch (e) {
      return []
    }
  })

  ipcMain.removeHandler('get-system-stats')
  ipcMain.handle('get-system-stats', async () => {
    const totalMem = os.totalmem()
    const freeMem = os.freemem()
    const cpuUsage = getSystemCpuUsage()
    let temp = Math.round(38 + parseFloat(cpuUsage) * 0.4)
    try {
      const cpuTemp = await si.cpuTemperature()
      if (cpuTemp && cpuTemp.main && cpuTemp.main > 0) {
        temp = Math.round(cpuTemp.main)
      }
    } catch {}

    const osRelease = os.release()
    const osType = os.platform() === 'win32'
      ? (osRelease.startsWith('10.0.2') ? 'Windows 11' : 'Windows 10')
      : `${os.type()} ${osRelease}`

    return {
      cpu: cpuUsage,
      memory: {
        total: (totalMem / 1024 ** 3).toFixed(1) + ' GB',
        free: (freeMem / 1024 ** 3).toFixed(1) + ' GB',
        usedPercentage: (((totalMem - freeMem) / totalMem) * 100).toFixed(1)
      },
      temperature: temp,
      os: {
        type: osType,
        uptime: (os.uptime() / 3600).toFixed(1) + 'h'
      }
    }
  })

  ipcMain.removeHandler('get-drives')
  ipcMain.handle('get-drives', async () => {
    try {
      const cmd = `powershell "Get-PSDrive -PSProvider FileSystem | Select-Object Name, @{N='FreeGB';E={[math]::round($_.Free/1GB, 2)}}, @{N='TotalGB';E={[math]::round(($_.Used + $_.Free)/1GB, 2)}} | ConvertTo-Json"`
      const output = await runCommand(cmd)
      return output ? JSON.parse(output) : []
    } catch (e) {
      return []
    }
  })
}
