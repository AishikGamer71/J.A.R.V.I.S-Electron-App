/**
 * Managed local runtime for the J.A.R.V.I.S core and voice services.
 *
 * These are two processes inside one desktop product, not separately linked
 * applications. The Electron main process owns their lifetime and both bind to
 * loopback-only ports. This replaces the legacy external Hermes bootstrap for
 * the native J.A.R.V.I.S UI.
 */

import { spawn as nodeSpawn, type ChildProcess } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'

export const JARVIS_CORE_PORT = 8765
export const JARVIS_VOICE_PORT = 8766

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
  // First check workspace root venv (our primary, fully loaded Python environment)
  const rootVenv = platform === 'win32'
    ? path.join(workspaceRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(workspaceRoot, '.venv', 'bin', 'python')
  if (fs.existsSync(rootVenv)) return rootVenv

  // Next check service-specific venv
  const local = platform === 'win32'
    ? path.join(serviceRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(serviceRoot, '.venv', 'bin', 'python')
  if (fs.existsSync(local)) return local

  return rootVenv
}

/** Prefer the project venv so Electron uses the exact locked service runtime. */
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
  const sourceRoot = path.join(serviceRoot, 'src')
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
    AUTH_TOKEN: environment.AUTH_TOKEN || 'jarvis-local-dev-token',
    DATA_DIR: dataRoot,
    DATABASE_PATH: path.join(dataRoot, 'jarvis.db'),
    SANDBOX_ROOT: path.join(dataRoot, 'sandbox'),
    SKILLS_DIR: path.join(dataRoot, 'skills'),
    PYTHONPATH: [workspaceRoot, sourceRoot, serviceRoot, environment.PYTHONPATH].filter(Boolean).join(delimiter),
  }
}

async function healthCheck(baseUrl: string, expectedService: string): Promise<boolean> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 4_000)
  try {
    const response = await fetch(`${baseUrl}/health`, { signal: controller.signal })
    if (!response.ok) {
      return false
    }
    const body = (await response.json()) as any
    return body?.status === 'healthy' && body?.service === expectedService
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

async function waitForHealth(baseUrl: string, expectedService: string, timeoutMs = 45_000): Promise<void> {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await healthCheck(baseUrl, expectedService)) {
      return
    }
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  throw new Error(`${expectedService} did not become healthy at ${baseUrl} within ${timeoutMs / 1000}s`)
}

/**
 * Starts local services only when there is not already a healthy J.A.R.V.I.S
 * service on the port. This lets a developer run `npm run core` independently
 * while the desktop app attaches to it rather than spawning a duplicate.
 */
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
  private voice: ManagedService | null = null
  private startPromise: Promise<JarvisRuntimeStatus> | null = null

  constructor(options: JarvisRuntimeOptions) {
    this.appDataDir = options.appDataDir
    this.coreRoot = options.coreRoot
    this.workspaceRoot = options.workspaceRoot ?? process.cwd()
    this.log = options.log ?? (() => {})
    this.platform = options.platform ?? process.platform
    this.pythonCommand = options.pythonCommand
    this.spawn = options.spawn ?? nodeSpawn
    this.voiceRoot = options.voiceRoot
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
    this.stopService(this.core)
    this.stopService(this.voice)
    this.core = null
    this.voice = null
    this.startPromise = null
  }

  private async startServices(): Promise<JarvisRuntimeStatus> {
    this.core = await this.startService('core')

    const isUnified = fs.existsSync(path.join(this.workspaceRoot, 'backend', 'server.py'))
    if (isUnified) {
      this.log(`[jarvis-runtime] Unified backend operational on port ${JARVIS_CORE_PORT} (core + voice integrated)`)
      return {
        core: this.statusFor(this.core),
        voice: this.statusFor(this.core),
        voiceError: null,
      }
    }

    try {
      this.voice = await this.startService('voice')
      return {
        core: this.statusFor(this.core),
        voice: this.statusFor(this.voice),
        voiceError: null,
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error)
      this.log(`[jarvis-runtime] Voice service unavailable; text J.A.R.V.I.S remains available: ${message}`)
      this.voice = null
      return { core: this.statusFor(this.core), voice: null, voiceError: message }
    }
  }

  private async startService(service: ServiceName): Promise<ManagedService> {
    const isCore = service === 'core'
    const root = isCore ? this.coreRoot : this.voiceRoot
    const port = isCore ? JARVIS_CORE_PORT : JARVIS_VOICE_PORT
    const expectedService = isCore ? 'jarvis-core-service' : 'jarvis-voice-service'
    const baseUrl = `http://127.0.0.1:${port}`

    if (await healthCheck(baseUrl, expectedService)) {
      this.log(`[jarvis-runtime] Reusing ${expectedService} at ${baseUrl}`)
      return { baseUrl, child: null, service }
    }

    if (!fs.existsSync(root)) {
      throw new Error(`${expectedService} source directory is missing: ${root}`)
    }

    const python = resolveServicePython(root, {
      platform: this.platform,
      pythonCommand: this.pythonCommand,
      workspaceRoot: this.workspaceRoot,
    })
    const backendServer = path.join(this.workspaceRoot, 'backend', 'server.py')
    const useUnifiedBackend = isCore && fs.existsSync(backendServer)

    const args = isCore
      ? (useUnifiedBackend
          ? ['-u', '-m', 'uvicorn', 'backend.server:app', '--host', '127.0.0.1', '--port', String(port)]
          : ['-u', '-m', 'jarvis.main'])
      : ['-u', '-m', 'uvicorn', 'server:app', '--host', '127.0.0.1', '--port', String(port)]

    const cwd = useUnifiedBackend ? this.workspaceRoot : root

    const env = isCore
      ? buildJarvisServiceEnv({ appDataDir: this.appDataDir, serviceRoot: root })
      : { ...process.env, PORT: String(port) }

    this.log(`[jarvis-runtime] Starting ${expectedService} via ${python} (cwd: ${cwd})`)
    const child = this.spawn(python, args, {
      cwd,
      env,
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: false,
    })
    const managed = { baseUrl, child, service }

    this.log(`[jarvis-runtime] ${expectedService} spawned with pid=${child.pid}`)
    child.on('error', err => this.log(`[jarvis-runtime] ${expectedService} process error: ${err.message}`))
    child.stdout?.on('data', chunk => this.log(`[${expectedService}] ${String(chunk).trim()}`))
    child.stderr?.on('data', chunk => this.log(`[${expectedService}] ${String(chunk).trim()}`))
    child.once('exit', (code, signal) => {
      this.log(`[jarvis-runtime] ${expectedService} exited (${signal || code})`)
      if (service === 'core' && this.core?.child === child) {
        this.core = null
      }
      if (service === 'voice' && this.voice?.child === child) {
        this.voice = null
      }
    })

    try {
      await waitForHealth(baseUrl, expectedService)
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
    if (!service?.child || service.child.killed) {
      return
    }
    const pid = service.child.pid
    try {
      if (this.platform === 'win32' && pid) {
        try {
          const { execSync } = require('node:child_process')
          execSync(`taskkill /pid ${pid} /T /F`, { stdio: 'ignore' })
        } catch {}
      }
      service.child.kill('SIGTERM')
    } catch {
      // The process may already have exited.
    }
  }
}
