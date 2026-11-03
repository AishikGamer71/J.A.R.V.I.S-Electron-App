/**
 * Managed local runtime for the J.A.R.V.I.S Python Sidecar.
 *
 * The Electron main process owns the lifetime of the Python FastAPI sidecar.
 * In development, it spawns Python from the workspace .venv.
 * In production, it executes the packaged sidecar binary or resources.
 * Guarantees zero zombie processes on exit via process-tree termination.
 */

import { spawn as nodeSpawn, execSync, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

export const JARVIS_CORE_PORT = 8765
export const JARVIS_VOICE_PORT = 8765 // Unified into single sidecar daemon

type ServiceName = 'core' | 'voice'
type SpawnLike = typeof nodeSpawn

export type JarvisServiceStatus = {
  baseUrl: string
  managed: boolean
  running: boolean
}

export type JarvisRuntimeStatus = {
  core: JarvisServiceStatus
  voice: JarvisServiceStatus | null
  voiceError: string | null
}

export type JarvisRuntimeOptions = {
  appDataDir: string
  coreRoot: string
  workspaceRoot?: string
  log?: (message: string) => void
  platform?: NodeJS.Platform
  pythonCommand?: string
  spawn?: SpawnLike
  voiceRoot: string
}

type ManagedService = {
  baseUrl: string
  child: ChildProcess | null
  service: ServiceName
}

function venvPythonPath(serviceRoot: string, platform: NodeJS.Platform, workspaceRoot: string = process.cwd()): string {
  // 1. Workspace root virtual environment (recommended)
  const rootVenv = platform === 'win32'
    ? path.join(workspaceRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(workspaceRoot, '.venv', 'bin', 'python')
  if (fs.existsSync(rootVenv)) return rootVenv

  // 2. Service-specific venv fallback
  const local = platform === 'win32'
    ? path.join(serviceRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(serviceRoot, '.venv', 'bin', 'python')
  if (fs.existsSync(local)) return local

  return rootVenv
}

export function resolveServicePython(
  serviceRoot: string,
  { exists = fs.existsSync, platform = process.platform, pythonCommand = process.env.JARVIS_PYTHON, workspaceRoot = process.cwd() }: {
    exists?: (path: string) => boolean
    platform?: NodeJS.Platform
    pythonCommand?: string
    workspaceRoot?: string
  } = {}
): string {
  if (pythonCommand?.trim()) {
    return pythonCommand.trim()
  }

  // Packaged production mode resolution
  try {
    const electron = require('electron')
    const app = electron.app || electron.remote?.app
    if (app?.isPackaged) {
      const resources = process.resourcesPath || ''
      const prodExe = platform === 'win32'
        ? path.join(resources, 'backend', 'jarvis-sidecar.exe')
        : path.join(resources, 'backend', 'jarvis-sidecar')
      if (exists(prodExe)) {
        return prodExe
      }
    }
  } catch {}

  const venvPython = venvPythonPath(serviceRoot, platform, workspaceRoot)
  if (exists(venvPython)) {
    return venvPython
  }

  return platform === 'win32' ? 'python.exe' : 'python3'
}

export function buildJarvisServiceEnv({
  appDataDir,
  environment = process.env,
  serviceRoot
}: {
  appDataDir: string
  environment?: NodeJS.ProcessEnv
  serviceRoot: string
}): NodeJS.ProcessEnv {
  const delimiter = process.platform === 'win32' ? ';' : ':'
  const workspaceRoot = process.cwd()
  const dataRoot = path.join(appDataDir, 'core')
  const venvDir = path.join(workspaceRoot, '.venv')
  const venvScripts = process.platform === 'win32' ? path.join(venvDir, 'Scripts') : path.join(venvDir, 'bin')
  const currentPath = environment.PATH || environment.Path || ''

  try {
    fs.mkdirSync(dataRoot, { recursive: true })
  } catch {}

  return {
    ...environment,
    PATH: [venvScripts, currentPath].filter(Boolean).join(delimiter),
    Path: [venvScripts, currentPath].filter(Boolean).join(delimiter),
    VIRTUAL_ENV: venvDir,
    PYTHONUNBUFFERED: '1',
    PORT: String(JARVIS_CORE_PORT),
    DATA_DIR: dataRoot,
    DATABASE_PATH: path.join(workspaceRoot, 'storage', 'jarvis_memory.db'),
    PYTHONPATH: [workspaceRoot, serviceRoot, environment.PYTHONPATH].filter(Boolean).join(delimiter),
  }
}

async function healthCheck(baseUrl: string, expectedService: string): Promise<boolean> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 3_000)
  try {
    const response = await fetch(`${baseUrl}/health`, { signal: controller.signal })
    if (!response.ok) {
      return false
    }
    const body = (await response.json()) as any
    return body?.status === 'healthy'
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

async function waitForHealth(baseUrl: string, expectedService: string, timeoutMs = 30_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await healthCheck(baseUrl, expectedService)) {
      return
    }
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  throw new Error(`${expectedService} did not become healthy at ${baseUrl} within ${timeoutMs / 1000}s`)
}

export class JarvisServiceRuntime {
  private readonly appDataDir: string
  private readonly coreRoot: string
  private readonly workspaceRoot: string
  private readonly log: (message: string) => void
  private readonly platform: NodeJS.Platform
  private readonly pythonCommand?: string
  private readonly spawn: SpawnLike
  private readonly voiceRoot: string
  private core: ManagedService | null = null
  private startPromise: Promise<JarvisRuntimeStatus> | null = null
  private isTerminating = false

  constructor(options: JarvisRuntimeOptions) {
    this.appDataDir = options.appDataDir
    this.coreRoot = options.coreRoot
    this.workspaceRoot = options.workspaceRoot ?? process.cwd()
    this.log = options.log ?? (() => {})
    this.platform = options.platform ?? process.platform
    this.pythonCommand = options.pythonCommand
    this.spawn = options.spawn ?? nodeSpawn
    this.voiceRoot = options.voiceRoot

    // Attach process-level lifecycle handlers to prevent zombie daemons
    const cleanExit = () => this.stop()
    process.once('exit', cleanExit)
    process.once('SIGINT', cleanExit)
    process.once('SIGTERM', cleanExit)

    try {
      const electron = require('electron')
      const app = electron.app
      if (app) {
        app.once('before-quit', cleanExit)
        app.once('will-quit', cleanExit)
      }
    } catch {}
  }

  start(): Promise<JarvisRuntimeStatus> {
    if (!this.startPromise) {
      this.startPromise = this.startServices().catch(error => {
        this.startPromise = null
        throw error
      })
    }
    return this.startPromise
  }

  stop(): void {
    this.isTerminating = true
    this.stopService(this.core)
    this.core = null
    this.startPromise = null
  }

  private async startServices(): Promise<JarvisRuntimeStatus> {
    this.core = await this.startUnifiedBackend()
    return {
      core: this.statusFor(this.core),
      voice: this.statusFor(this.core),
      voiceError: null,
    }
  }

  private async startUnifiedBackend(): Promise<ManagedService> {
    const port = JARVIS_CORE_PORT
    const expectedService = 'jarvis-core-service'
    const baseUrl = `http://127.0.0.1:${port}`

    if (await healthCheck(baseUrl, expectedService)) {
      this.log(`[jarvis-runtime] Reusing healthy ${expectedService} on ${baseUrl}`)
      return { baseUrl, child: null, service: 'core' }
    }

    const python = resolveServicePython(this.workspaceRoot, {
      platform: this.platform,
      pythonCommand: this.pythonCommand,
      workspaceRoot: this.workspaceRoot,
    })

    const hasMainPy = fs.existsSync(path.join(this.workspaceRoot, 'backend', 'main.py'))
    const appModule = hasMainPy ? 'backend.main:app' : 'backend.server:app'

    const args = [
      '-u',
      '-m',
      'uvicorn',
      appModule,
      '--host',
      '127.0.0.1',
      '--port',
      String(port)
    ]

    const cwd = this.workspaceRoot
    const env = buildJarvisServiceEnv({
      appDataDir: this.appDataDir,
      serviceRoot: this.workspaceRoot
    })

    this.log(`[jarvis-runtime] Spawning ${appModule} via ${python} in ${cwd}`)
    const child = this.spawn(python, args, {
      cwd,
      env,
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: false,
    })

    const managed: ManagedService = { baseUrl, child, service: 'core' }

    this.log(`[jarvis-runtime] Sidecar spawned successfully with pid=${child.pid}`)
    child.on('error', err => this.log(`[jarvis-runtime] Sidecar process error: ${err.message}`))
    child.stdout?.on('data', chunk => this.log(`[sidecar] ${String(chunk).trim()}`))
    child.stderr?.on('data', chunk => this.log(`[sidecar:err] ${String(chunk).trim()}`))

    child.once('exit', (code, signal) => {
      this.log(`[jarvis-runtime] Sidecar exited with signal=${signal} code=${code}`)
      if (this.core?.child === child) {
        this.core = null
      }
      // Auto-restart if unexpected termination and not shutting down
      if (!this.isTerminating && code !== 0) {
        this.log('[jarvis-runtime] Sidecar crashed unexpectedly. Scheduling auto-recovery...')
        setTimeout(() => {
          if (!this.isTerminating && !this.core) {
            this.startServices().catch(e => this.log(`[jarvis-runtime] Recovery failed: ${e}`))
          }
        }, 2000)
      }
    })

    try {
      await waitForHealth(baseUrl, expectedService, 30_000)
      this.log(`[jarvis-runtime] Sidecar is healthy and accepting WebSocket connections at ${baseUrl}/ws/jarvis`)
      return managed
    } catch (error) {
      this.stopService(managed)
      throw error
    }
  }

  private statusFor(service: ManagedService): JarvisServiceStatus {
    return {
      baseUrl: service.baseUrl,
      managed: service.child !== null,
      running: service.child ? service.child.exitCode === null && !service.child.killed : true,
    }
  }

  private stopService(service: ManagedService | null): void {
    if (!service?.child) {
      return
    }
    const pid = service.child.pid
    if (!pid) return

    this.log(`[jarvis-runtime] Terminating sidecar process tree (pid=${pid})...`)
    try {
      if (this.platform === 'win32') {
        try {
          execSync(`taskkill /pid ${pid} /T /F`, { stdio: 'ignore' })
        } catch {}
      } else {
        try {
          process.kill(-pid, 'SIGTERM')
        } catch {
          service.child.kill('SIGTERM')
        }
      }
    } catch {
      // Process already terminated
    }
  }
}
