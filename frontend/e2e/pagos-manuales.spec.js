import { mkdirSync, readFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const localGuide = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/USUARIOS_PRUEBA_LOCAL.md')
const screenshots = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../test-results')

function leerCuentas() {
  const contenido = readFileSync(localGuide, 'utf8')
  const bloque = contenido.match(/```json\n([\s\S]*?)\n```/)
  if (!bloque) throw new Error('El seeder no dejó un archivo local de credenciales válido.')
  const usuarios = JSON.parse(bloque[1]).usuarios
  return { jugador: usuarios.jugador, cajero: usuarios.cajero_a }
}

function lunesDesde(fecha, semanas) {
  const siguiente = new Date(`${fecha}T00:00:00Z`)
  siguiente.setUTCDate(siguiente.getUTCDate() + semanas * 7)
  return siguiente.toISOString().slice(0, 10)
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

async function ingresar(page, cuenta, destino) {
  await page.goto('/ingresar')
  await page.getByLabel('Correo electrónico').fill(cuenta.correo)
  await page.getByLabel('Contraseña').fill(cuenta.contrasena)
  await page.getByRole('button', { name: 'Iniciar sesión' }).click()
  await expect(page).toHaveURL(new RegExp(`${destino}$`))
}

async function seleccionarHorarioLibre(page) {
  const base = proximoLunesLima()
  await page.goto('/canchas-publicas')
  const selector = page.getByLabel('Cancha publicada')
  await expect(selector).toContainText('Cancha A heredada')
  const opciones = await selector.locator('option').allTextContents()
  const etiqueta = opciones.find((opcion) => opcion.includes('Cancha A heredada'))
  await selector.selectOption({ label: etiqueta })

  for (let semana = 0; semana < 10; semana += 1) {
    await page.getByLabel('Fecha del calendario').fill(lunesDesde(base, semana))
    await expect(page.getByTestId('bloque-calendario').first()).toBeVisible()
    const disponibles = page.getByRole('button', { name: 'Seleccionar horario' })
    if (await disponibles.count()) {
      await disponibles.first().click()
      return
    }
  }
  throw new Error('No se encontró un horario libre en las próximas diez semanas para la prueba.')
}

test('jugador declara un adelanto y cajero lo verifica manualmente', async ({ browser }) => {
  const { jugador, cajero } = leerCuentas()
  const contextoJugador = await browser.newContext({
    colorScheme: 'light', viewport: { width: 390, height: 844 },
  })
  const contextoCajero = await browser.newContext({
    colorScheme: 'dark', viewport: { width: 1440, height: 1000 },
  })
  const jugadorPage = await contextoJugador.newPage()
  const cajeroPage = await contextoCajero.newPage()
  let codigoReserva = ''

  try {
    await ingresar(jugadorPage, jugador, '/panel/jugador')
    await seleccionarHorarioLibre(jugadorPage)
    await jugadorPage.getByRole('button', { name: 'Calcular importe' }).click()
    await expect(jugadorPage.getByText('Total de la reserva')).toBeVisible()
    await jugadorPage.getByRole('button', { name: 'Solicitar reserva temporal' }).click()
    const detalleReserva = jugadorPage.getByRole('dialog')
    const respuestaReserva = jugadorPage.waitForResponse((respuesta) => (
      respuesta.request().method() === 'POST' && new URL(respuesta.url()).pathname === '/api/reservas/'
    ))
    await detalleReserva.getByRole('button', { name: 'Apartar horario' }).click()
    const respuesta = await respuestaReserva
    expect(respuesta.status()).toBe(201)
    codigoReserva = (await respuesta.json()).codigo
    await expect(detalleReserva.getByText('Horario retenido temporalmente')).toBeVisible()

    await jugadorPage.goto(`/mis-reservas/${codigoReserva}/pago`)
    await expect(jugadorPage.getByText('Adelanto mínimo · 50%')).toBeVisible()
    const solicitud = jugadorPage.waitForResponse((respuestaPago) => (
      respuestaPago.request().method() === 'POST'
      && new URL(respuestaPago.url()).pathname === `/api/pagos/reservas/${codigoReserva}/solicitudes/`
    ))
    await jugadorPage.getByLabel('He leído y acepto las condiciones de cancelación de la sede.').check()
    await jugadorPage.getByRole('button', { name: /Continuar ·/ }).click()
    expect((await solicitud).status()).toBe(201)

    const whatsapp = jugadorPage.getByRole('link', { name: 'Abrir WhatsApp para adjuntar captura' })
    await expect(whatsapp).toHaveAttribute('href', /https:\/\/wa\.me\/00000000000\?text=/)
    await expect(whatsapp).toHaveAttribute('target', '_blank')
    const textoWhatsApp = new URL(await whatsapp.getAttribute('href')).searchParams.get('text')
    expect(textoWhatsApp).toContain(codigoReserva)
    expect(textoWhatsApp).toContain('Monto a verificar: S/ ')
    await jugadorPage.getByLabel(/Referencia o código de operación/).fill('DEMO-REF-4C')
    const declaracion = jugadorPage.waitForResponse((respuestaPago) => (
      respuestaPago.request().method() === 'POST'
      && new URL(respuestaPago.url()).pathname.includes('/declarar/')
    ))
    await jugadorPage.getByRole('button', { name: 'Ya envié mi comprobante' }).click()
    expect((await declaracion).status()).toBe(200)
    await expect(jugadorPage.getByRole('heading', { name: 'La sede revisará tu comprobante' })).toBeVisible()
    await expect(jugadorPage.getByText('no aprueban el pago automáticamente')).toBeVisible()
    await expect(jugadorPage.getByText('Tu reserva no queda confirmada')).toBeVisible()
    mkdirSync(screenshots, { recursive: true })
    await jugadorPage.screenshot({ path: path.join(screenshots, 'pagos-jugador-revision.png'), fullPage: true })

    await ingresar(cajeroPage, cajero, '/panel/cajero')
    await cajeroPage.getByRole('button', { name: 'Pagos', exact: true }).click()
    const filaPago = cajeroPage.getByRole('row').filter({ hasText: codigoReserva })
    await expect(filaPago).toBeVisible()
    await filaPago.getByRole('button', { name: 'Revisar' }).click()
    const revision = cajeroPage.getByRole('dialog')
    await expect(revision.getByText(codigoReserva)).toBeVisible()
    await expect(revision.getByText('El personal debe comprobar el movimiento en su cuenta.')).toBeVisible()
    const importe = await revision.locator('input[type="number"]').inputValue()
    await revision.locator('input[type="number"]').fill(importe)
    await revision.screenshot({ path: path.join(screenshots, 'pagos-cajero-modal-oscuro.png') })

    const aprobacion = cajeroPage.waitForResponse((respuestaPago) => (
      respuestaPago.request().method() === 'POST'
      && new URL(respuestaPago.url()).pathname.endsWith('/aprobar/')
    ))
    await revision.getByRole('button', { name: 'Aprobar pago' }).click()
    expect((await aprobacion).status()).toBe(200)
    await expect(cajeroPage.getByRole('status').filter({ hasText: 'La reserva está confirmada' })).toBeVisible()
    await expect(revision.getByText('Pago revisado', { exact: true })).toBeVisible()
    await expect(revision.getByText('QR', { exact: false })).toHaveCount(0)
    await revision.getByRole('button', { name: 'Cerrar', exact: true }).click()
    await cajeroPage.getByRole('button', { name: 'Reservas', exact: true }).click()
    const ingreso = cajeroPage.getByRole('region', { name: 'Validar ingreso' })
    await expect(ingreso).toBeVisible()
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-escritorio-oscuro.png') })
    await cajeroPage.setViewportSize({ width: 390, height: 844 })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-movil-oscuro.png'), animations: 'disabled' })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-movil-claro.png') })

    await jugadorPage.goto('/mis-reservas')
    const filaReserva = jugadorPage.getByRole('row').filter({ hasText: codigoReserva })
    await expect(filaReserva).toBeVisible()
    await filaReserva.getByRole('button', { name: 'Ver ticket' }).click()
    const ticket = jugadorPage.getByRole('dialog')
    await expect(ticket.getByAltText('Código QR de la reserva confirmada')).toBeVisible()
    await expect(ticket.getByRole('link', { name: 'Descargar QR' })).toBeVisible()
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-movil-claro.png') })
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-movil-oscuro.png'), animations: 'disabled' })
    await jugadorPage.setViewportSize({ width: 1440, height: 1000 })
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-escritorio-oscuro.png') })
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-escritorio-claro.png') })
    await ticket.getByRole('button', { name: 'Cerrar', exact: true }).click()
    await filaReserva.getByRole('button', { name: 'Ver detalle' }).click()
    await jugadorPage.getByRole('dialog').getByRole('button', { name: 'Cancelar reserva' }).click()
    const cancelar = jugadorPage.getByRole('dialog')
    await expect(cancelar.getByText('Las cancelaciones voluntarias normalmente no generan devolución del adelanto. Las excepciones y los derechos aplicables pueden requerir revisión de la sede.', { exact: true })).toBeVisible()
    await cancelar.screenshot({ path: path.join(screenshots, '4d-cancelacion-escritorio-claro.png') })
    await jugadorPage.setViewportSize({ width: 390, height: 844 })
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await cancelar.screenshot({ path: path.join(screenshots, '4d-cancelacion-movil-oscuro.png') })
    await cancelar.getByLabel('Motivo de cancelación').fill('Prueba local de cancelación')
    await cancelar.getByRole('button', { name: 'Confirmar cancelación' }).click()
    await expect(jugadorPage.getByRole('status').filter({ hasText: 'Reserva cancelada' })).toBeVisible()
    await expect(filaReserva.getByText('Cancelada')).toBeVisible()

  } finally {
    await contextoJugador.close()
    await contextoCajero.close()
  }
})
