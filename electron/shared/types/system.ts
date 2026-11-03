/**
 * System information types shared between Main process and Renderer.
 */

export interface SystemStats {
  cpu: string
  memory: {
    total: string
    free: string
    usedPercentage: string
  }
  temperature: number
  os: {
    type: string
    uptime: string
  }
}

export interface AppItem {
  name: string
  id: string
}

export interface DriveInfo {
  name: string
  mount: string
  type: string
  size: number
  used: number
  available: number
}
