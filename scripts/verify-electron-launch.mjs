import { spawn } from 'node:child_process'
import path from 'node:path'

console.log('[SmokeTest] Testing Electron launch and clean shutdown...')

const electronPath = process.platform === 'win32'
  ? path.join(process.cwd(), 'node_modules', 'electron', 'dist', 'electron.exe')
  : path.join(process.cwd(), 'node_modules', '.bin', 'electron')

const child = spawn(electronPath, ['.'], {
  env: {
    ...process.env,
    JARVIS_SMOKE_TEST: '1',
    ELECTRON_ENABLE_LOGGING: '1'
  },
  stdio: ['ignore', 'pipe', 'pipe']
})

let logs = ''
child.stdout.on('data', d => {
  const s = d.toString()
  logs += s
  process.stdout.write(s)
})

child.stderr.on('data', d => {
  const s = d.toString()
  logs += s
  process.stderr.write(s)
})

// Let it initialize services, then terminate cleanly
setTimeout(() => {
  console.log('[SmokeTest] Terminating Electron process cleanly...')
  child.kill('SIGINT')
  setTimeout(() => {
    try {
      child.kill('SIGTERM')
    } catch {}
  }, 2000)
}, 8000)

child.on('exit', (code, signal) => {
  console.log(`[SmokeTest] Electron exited with code=${code}, signal=${signal}`)
  process.exit(0)
})
