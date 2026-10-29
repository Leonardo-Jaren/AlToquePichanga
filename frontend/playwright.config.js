import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.resolve(frontendDir, '../backend')
const backendPort = 18200
const frontendPort = 15173
const pythonPath = process.env.ALTOQUE_PYTHON || (process.platform === 'win32'
  ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
  : path.join(backendDir, 'venv', 'bin', 'python'))

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/prepararDatos.js',
  fullyParallel: false,
  workers: 1,
  timeout: 90000,
  reporter: 'line',
  outputDir: './test-results',
  use: {
    baseURL: `http://localhost:${frontendPort}`,
    browserName: 'chromium',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    actionTimeout: 15000,
  },
  webServer: [
    {
      command: `"${pythonPath}" manage.py runserver 127.0.0.1:${backendPort} --noreload`,
      cwd: backendDir,
      url: `http://127.0.0.1:${backendPort}/api/health/`,
      reuseExistingServer: false,
      timeout: 60000,
      env: {
        DEBUG: 'True',
        USE_REDIS_CHANNEL_LAYER: 'False',
        FRONTEND_URL: `http://localhost:${frontendPort}`,
        CORS_ALLOWED_ORIGINS: `http://localhost:${frontendPort},http://127.0.0.1:${frontendPort}`,
      },
    },
    {
      command: `npm run dev -- --host localhost --port ${frontendPort} --strictPort`,
      cwd: frontendDir,
      url: `http://localhost:${frontendPort}`,
      reuseExistingServer: false,
      timeout: 60000,
      env: { VITE_API_BASE_URL: `http://localhost:${backendPort}/api` },
    },
  ],
})
