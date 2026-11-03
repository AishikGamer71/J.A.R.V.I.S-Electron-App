#!/usr/bin/env node
// Run J.A.R.V.I.S sidecar backend outside Electron for development and diagnostics.

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import process from 'node:process'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const rootVenvPython = process.platform === 'win32'
  ? join(root, '.venv', 'Scripts', 'python.exe')
  : join(root, '.venv', 'bin', 'python')

const python = process.env.JARVIS_PYTHON || (existsSync(rootVenvPython) ? rootVenvPython : (process.platform === 'win32' ? 'python.exe' : 'python3'))
const port = process.env.PORT || '8765'

const hasMainPy = existsSync(join(root, 'backend', 'main.py'))
const appModule = hasMainPy ? 'backend.main:app' : 'backend.server:app'

const args = ['-m', 'uvicorn', appModule, '--host', '127.0.0.1', '--port', port, '--reload']
const env = {
  ...process.env,
  PORT: port,
  PYTHONPATH: [root, process.env.PYTHONPATH].filter(Boolean).join(process.platform === 'win32' ? ';' : ':'),
}

console.log(`[run-jarvis-service] Spawning ${appModule} on port ${port} using ${python}`)
const child = spawn(python, args, { cwd: root, env, stdio: 'inherit', shell: false })
child.once('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0)
})
