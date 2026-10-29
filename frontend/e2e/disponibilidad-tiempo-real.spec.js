import { readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const localGuide = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/USUARIOS_PRUEBA_LOCAL.md')

function leerCredenciales() {
  const contenido = readFileSync(localGuide, 'utf8')
  const bloque = contenido.match(/```json\n([\s\S]*?)\n```/)
  if (!bloque) throw new Error('El seeder no dejó un archivo local de credenciales válido.')
  const usuarios = JSON.parse(bloque[1]).usuarios
  return [usuarios.jugador, usuarios.jugador_b]
}

function proximoLunesLima() {
  const partes = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short',
  }).formatToParts(new Date()).map((parte) => [parte.type, parte.value]))
  const hoy = new Date(Date.UTC(Number(partes.year), Number(partes.month) - 1, Number(partes.day)))
  const diferencia = (8 - hoy.getUTCDay()) % 7 || 7
  hoy.setUTCDate(hoy.getUTCDate() + diferencia)
  return hoy.toISOString().slice(0, 10)
}

async function ingresar(page, cuenta) {
  await page.goto('/ingresar')
  await page.getByLabel('Correo electrónico').fill(cuenta.correo)
  await page.getByLabel('Contraseña').fill(cuenta.contrasena)
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
  await expect(page).toHaveURL(/\/panel\/jugador$/)
}

async function abrirCalendario(page, fecha) {
  await page.goto('/canchas-publicas')
  await seleccionarCanchaDemo(page)
  await page.getByLabel('Fecha del calendario').fill(fecha)
  await expect(page.getByTestId('bloque-calendario').filter({ hasText: '19:00–20:00' })).toBeVisible()
  await expect(page.getByText('En vivo')).toBeVisible()
}

async function seleccionarCanchaDemo(page) {
  const selector = page.getByLabel('Cancha publicada')
  await expect(selector).toContainText('Cancha A heredada')
  const opciones = await selector.locator('option').allTextContents()
  const etiqueta = opciones.find((opcion) => opcion.includes('Cancha A heredada'))
  if (!etiqueta) throw new Error('No aparece la cancha demo publicada en el catálogo local.')
  await selector.selectOption({ label: etiqueta })
}

test('dos jugadores reciben retención y liberación sin recargar', async ({ browser }) => {
  const [jugadorA, jugadorB] = leerCredenciales()
  const fecha = proximoLunesLima()
  const contextoA = await browser.newContext({ colorScheme: 'light' })
  const contextoB = await browser.newContext({ colorScheme: 'dark' })
  const paginaA = await contextoA.newPage()
  const paginaB = await contextoB.newPage()
  let codigoReserva = ''

  try {
    await ingresar(paginaA, jugadorA)
    await ingresar(paginaB, jugadorB)
    await Promise.all([abrirCalendario(paginaA, fecha), abrirCalendario(paginaB, fecha)])

    const bloqueA = paginaA.getByTestId('bloque-calendario').filter({ hasText: '19:00–20:00' })
    const bloqueB = paginaB.getByTestId('bloque-calendario').filter({ hasText: '19:00–20:00' })
    await expect(bloqueA.getByRole('button', { name: 'Seleccionar horario' })).toBeEnabled()
    await expect(bloqueB.getByRole('button', { name: 'Seleccionar horario' })).toBeEnabled()

    await bloqueA.getByRole('button', { name: 'Seleccionar horario' }).click()
    await paginaA.getByRole('button', { name: 'Calcular importe' }).click()
    await expect(paginaA.getByText('Total de la reserva')).toBeVisible()
    await paginaA.getByRole('button', { name: 'Solicitar reserva temporal' }).click()
    const dialogo = paginaA.getByRole('dialog')
    const respuestaReserva = paginaA.waitForResponse((respuesta) => (
      respuesta.request().method() === 'POST' && new URL(respuesta.url()).pathname === '/api/reservas/'
    ))
    await dialogo.getByRole('button', { name: 'Apartar horario' }).click()
    const respuesta = await respuestaReserva
    expect(respuesta.status()).toBe(201)
    codigoReserva = (await respuesta.json()).codigo
    await expect(dialogo.getByText('Horario retenido temporalmente')).toBeVisible()

    await expect(bloqueB.getByText('Retenida temporalmente')).toBeVisible({ timeout: 10000 })
    await expect(bloqueB.getByRole('button', { name: 'Seleccionar horario' })).toHaveCount(0)

    await paginaA.goto('/mis-reservas')
    const fila = paginaA.getByRole('row').filter({ hasText: codigoReserva })
    await fila.getByRole('button', { name: 'Ver detalle' }).click()
    const detalle = paginaA.getByRole('dialog')
    await detalle.getByRole('button', { name: 'Cancelar retención' }).click()
    await detalle.getByRole('button', { name: 'Sí, cancelar' }).click()

    await paginaB.goto('/canchas-publicas')
    await seleccionarCanchaDemo(paginaB)
    await paginaB.getByLabel('Fecha del calendario').fill(fecha)
    const bloqueLiberado = paginaB.getByTestId('bloque-calendario').filter({ hasText: '19:00–20:00' })
    await expect(bloqueLiberado.getByRole('button', { name: 'Seleccionar horario' })).toBeEnabled({ timeout: 10000 })
  } finally {
    await paginaA.goto('/mis-reservas').catch(() => {})
    const filas = codigoReserva
      ? paginaA.getByRole('row').filter({ hasText: codigoReserva })
      : paginaA.getByRole('row').filter({ hasText: 'Cancha A heredada' }).filter({ hasText: '19:00–20:00' })
    const cantidad = await filas.count().catch(() => 0)
    for (let indice = 0; indice < cantidad; indice += 1) {
      const fila = filas.nth(indice)
      await fila.getByRole('button', { name: 'Ver detalle' }).click().catch(() => {})
      const dialogo = paginaA.getByRole('dialog')
      if (await dialogo.getByRole('button', { name: 'Cancelar retención' }).count().catch(() => 0)) {
        await dialogo.getByRole('button', { name: 'Cancelar retención' }).click().catch(() => {})
        await dialogo.getByRole('button', { name: 'Sí, cancelar' }).click().catch(() => {})
      } else {
        await dialogo.getByRole('button', { name: 'Cerrar' }).click().catch(() => {})
      }
    }
    await contextoA.close()
    await contextoB.close()
  }
})
