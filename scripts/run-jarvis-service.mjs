#!/usr/bin/env node
// Run one J.A.R.V.I.S service outside Electron for development and diagnostics.

import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { resolve, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import process from 'node:process'

const service = process.argv[2]
const root = resolve(fileURLToPath(new URL('..', import.meta.url)))

if (service !== 'core' && service !== 'voice') {
  console.error('Usage: node scripts/run-jarvis-service.mjs <core|voice>')
  process.exitCode = 1
} else {
  const serviceRoot = join(root, service === 'core' ? 'apps/core-service' : 'services/voice-service')
  const venvPython = process.platform === 'win32'
    ? join(serviceRoot, '.venv', 'Scripts', 'python.exe')
    : join(serviceRoot, '.venv', 'bin', 'python')
  const python = process.env.JARVIS_PYTHON || (existsSync(venvPython) ? venvPython : process.platform === 'win32' ? 'python.exe' : 'python3')
  const port = service === 'core' ? '8765' : '8766'
  const args = service === 'core'
    ? ['-m', 'jarvis.main']
    : ['-m', 'uvicorn', 'server:app', '--host', '127.0.0.1', '--port', port]
  const env = {
    ...process.env,
    PORT: port,
    PYTHONPATH: service === 'core'
      ? [join(serviceRoot, 'src'), process.env.PYTHONPATH].filter(Boolean).join(process.platform === 'win32' ? ';' : ':')
      : process.env.PYTHONPATH,
  }

  const child = spawn(python, args, { cwd: serviceRoot, env, stdio: 'inherit', shell: false })
  child.once('exit', (code, signal) => {
    process.exitCode = code ?? (signal ? 1 : 0)
  })
}
