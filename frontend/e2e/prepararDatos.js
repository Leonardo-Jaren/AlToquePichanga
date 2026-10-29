import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backendDir = path.resolve(frontendDir, '../backend')
const pythonPath = process.env.ALTOQUE_PYTHON || (process.platform === 'win32'
  ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
  : path.join(backendDir, 'venv', 'bin', 'python'))

export default function prepararDatos() {
  const resultado = spawnSync(pythonPath, ['manage.py', 'generar_datos_demo'], {
    cwd: backendDir,
    env: { ...process.env, ALTOQUE_PERMITIR_DATOS_DEMO: '1' },
    encoding: 'utf8',
  })
  if (resultado.error || resultado.status !== 0) {
    throw new Error([
      'No se pudieron preparar los datos locales para Playwright.',
      'El seeder exige DEBUG=True y PostgreSQL en loopback; no ejecuta contra producción.',
      resultado.stderr,
    ].filter(Boolean).join('\n'))
  }
}
