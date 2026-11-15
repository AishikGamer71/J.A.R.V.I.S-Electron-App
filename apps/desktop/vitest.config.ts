import type { TestProjectConfiguration } from 'vitest/config';
import { defineConfig } from 'vitest/config'
import path from 'path'

const repoRoot = path.resolve(__dirname, '../..')

const reactUi: TestProjectConfiguration = {
  root: repoRoot,
  extends: './apps/desktop/vite.config.ts',
  test: {
    name: 'ui',
    environment: 'jsdom',
    setupFiles: ['./apps/desktop/vitest.setup.ts'],
    include: ['apps/desktop/src/**/*.test.{ts,tsx}'],
    globals: true,
    testTimeout: 15_000
  }
}

const electronNative: TestProjectConfiguration = {
  root: repoRoot,
  test: {
    name: 'electron',
    environment: 'node',
    configFile: false,
    include: ['apps/desktop/electron/**/*.test.ts', 'scripts/**/*.test.{ts,mjs}']
  }
}

export default defineConfig({
  root: repoRoot,
  test: {
    projects: [reactUi, electronNative]
  }
})
