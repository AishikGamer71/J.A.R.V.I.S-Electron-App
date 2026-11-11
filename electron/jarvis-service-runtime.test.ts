import path from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildJarvisServiceEnv, resolveServicePython } from './jarvis-service-runtime'

describe('J.A.R.V.I.S local service runtime', () => {
  it('prefers the project virtual environment over a system Python', () => {
    const root = 'C:\\work\\jarvis-core'
    const expected = path.join(root, '.venv', 'Scripts', 'python.exe')

    expect(
      resolveServicePython(root, {
        platform: 'win32',
        exists: candidate => candidate === expected,
      })
    ).toBe(expected)
  })

  it('uses an explicit Python override when supplied', () => {
    expect(
      resolveServicePython('/work/jarvis-core', {
        platform: 'linux',
        pythonCommand: '/opt/python/bin/python',
      })
    ).toBe('/opt/python/bin/python')
  })

  it('isolates J.A.R.V.I.S data while preserving an existing PYTHONPATH', () => {
    const env = buildJarvisServiceEnv({
      appDataDir: '/app-data',
      serviceRoot: '/repo/apps/core-service',
      environment: { PYTHONPATH: '/existing/path' },
    })

    expect(env.DATA_DIR).toBe(path.join('/app-data', 'core'))
    expect(env.DATABASE_PATH).toBe(path.join('/app-data', 'core', 'jarvis.db'))
    expect(env.SKILLS_DIR).toBe(path.join('/app-data', 'core', 'skills'))
    expect(env.PYTHONPATH).toContain(path.join('/repo/apps/core-service', 'src'))
    expect(env.PYTHONPATH).toContain('/existing/path')
  })
})
