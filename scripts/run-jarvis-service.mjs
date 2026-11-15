#!/usr/bin/env node
// Run J.A.R.V.I.S sidecar backend outside Electron for development and diagnostics.

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import process from 'node:process'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const serviceBackend = join(root, 'services', 'backend')
const backendVenvPython = process.platform === 'win32'
  ? join(serviceBackend, '.venv', 'Scripts', 'python.exe')
  : join(serviceBackend, '.venv', 'bin', 'python')
const rootVenvPython = process.platform === 'win32'
  ? join(root, '.venv', 'Scripts', 'python.exe')
  : join(root, '.venv', 'bin', 'python')

const venvPython = existsSync(backendVenvPython) ? backendVenvPython : rootVenvPython
const python = process.env.JARVIS_PYTHON || (existsSync(venvPython) ? venvPython : (process.platform === 'win32' ? 'python.exe' : 'python3'))
const port = process.env.PORT || '8765'

const hasAppMainPy = existsSync(join(serviceBackend, 'app', 'main.py'))
const appModule = hasAppMainPy ? 'app.main:app' : (existsSync(join(root, 'backend', 'main.py')) ? 'backend.main:app' : 'backend.server:app')
const cwd = hasAppMainPy ? serviceBackend : root

const args = ['-m', 'uvicorn', appModule, '--host', '127.0.0.1', '--port', port, '--reload']
const env = {
  ...process.env,
  PORT: port,
  PYTHONPATH: [serviceBackend, root, process.env.PYTHONPATH].filter(Boolean).join(process.platform === 'win32' ? ';' : ':'),
}

console.log(`[run-jarvis-service] Spawning ${appModule} on port ${port} using ${python}`)
const child = spawn(python, args, { cwd, env, stdio: 'inherit', shell: false })
child.once('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0)
})
