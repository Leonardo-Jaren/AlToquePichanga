import { mkdirSync, readFileSync } from 'node:fs'
import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { expect, test } from '@playwright/test'

const localGuide = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/USUARIOS_PRUEBA_LOCAL.md')
const screenshots = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../test-results')
const frontendDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const backendDir = path.resolve(frontendDir, '../backend')
const pythonPath = process.env.ALTOQUE_PYTHON || (process.platform === 'win32'
  ? path.join(backendDir, 'venv', 'Scripts', 'python.exe')
  : path.join(backendDir, 'venv', 'bin', 'python'))

function leerCuentas() {
  const contenido = readFileSync(localGuide, 'utf8')
  const bloque = contenido.match(/```json\n([\s\S]*?)\n```/)
  if (!bloque) throw new Error('El seeder no dejó un archivo local de credenciales válido.')
  const usuarios = JSON.parse(bloque[1]).usuarios
  return {
    jugador: usuarios.jugador,
    cajero: usuarios.cajero_a,
    cajeroNorte: usuarios.cajero_a_norte,
  }
}

function prepararHorarioEnCurso(codigo) {
  const resultado = spawnSync(pythonPath, [
    'manage.py', 'preparar_asistencia_e2e', '--codigo', codigo,
  ], {
    cwd: backendDir,
    env: { ...process.env, DEBUG: 'True', ALTOQUE_PERMITIR_E2E_ASISTENCIA: '1' },
    encoding: 'utf8',
  })
  if (resultado.error || resultado.status !== 0) {
    throw new Error(`No se pudo controlar el horario de la reserva demo. ${resultado.stderr || ''}`)
  }
  return JSON.parse(resultado.stdout.trim())
}

function restaurarHorario(codigo, horario) {
  const resultado = spawnSync(pythonPath, [
    'manage.py', 'preparar_asistencia_e2e', '--codigo', codigo, '--restaurar',
    '--inicio-original', horario.inicio_original,
    '--fin-original', horario.fin_original,
    '--inicio-controlado', horario.inicio_controlado,
    '--fin-controlado', horario.fin_controlado,
  ], {
    cwd: backendDir,
    env: { ...process.env, DEBUG: 'True', ALTOQUE_PERMITIR_E2E_ASISTENCIA: '1' },
    encoding: 'utf8',
  })
  if (resultado.error || resultado.status !== 0) {
    throw new Error(`No se pudo restaurar el horario de la reserva demo. ${resultado.stderr || ''}`)
  }
}

async function prepararEscanerQr(page, token) {
  await page.evaluate((valor) => {
    Object.defineProperty(window, 'BarcodeDetector', { configurable: true, value: class {
      async detect() { return [{ rawValue: valor }] }
    } })
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: async () => new MediaStream() },
    })
    HTMLMediaElement.prototype.play = async () => {}
  }, token)
}

async function capturarAccionModal(dialogo, accion, nombreArchivo) {
  await dialogo.evaluate((elemento) => { elemento.scrollTop = elemento.scrollHeight })
  await expect(accion).toBeInViewport()
  await dialogo.screenshot({ path: path.join(screenshots, nombreArchivo) })
  await dialogo.evaluate((elemento) => { elemento.scrollTop = 0 })
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

test('jugador confirma, consulta el QR y cajero registra el ingreso una sola vez', async ({ browser }) => {
  const { jugador, cajero, cajeroNorte } = leerCuentas()
  const contextoJugador = await browser.newContext({
    colorScheme: 'light', viewport: { width: 390, height: 844 },
  })
  const contextoCajero = await browser.newContext({
    colorScheme: 'dark', viewport: { width: 1440, height: 1000 },
  })
  const contextoCajeroNorte = await browser.newContext({
    colorScheme: 'light', viewport: { width: 1440, height: 1000 },
  })
  const jugadorPage = await contextoJugador.newPage()
  const cajeroPage = await contextoCajero.newPage()
  const cajeroNortePage = await contextoCajeroNorte.newPage()
  let codigoReserva = ''
  let horarioControlado = null

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
    const botonAprobar = revision.getByRole('button', { name: 'Aprobar pago' })
    await revision.screenshot({ path: path.join(screenshots, '4d-pago-modal-escritorio-oscuro.png') })
    await capturarAccionModal(revision, botonAprobar, '4d-pago-modal-final-escritorio-oscuro.png')
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await revision.screenshot({ path: path.join(screenshots, '4d-pago-modal-escritorio-claro.png') })
    await capturarAccionModal(revision, botonAprobar, '4d-pago-modal-final-escritorio-claro.png')
    await cajeroPage.setViewportSize({ width: 390, height: 844 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await revision.screenshot({ path: path.join(screenshots, '4d-pago-modal-movil-oscuro.png') })
    await capturarAccionModal(revision, botonAprobar, '4d-pago-modal-final-movil-oscuro.png')
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await revision.screenshot({ path: path.join(screenshots, '4d-pago-modal-movil-claro.png') })
    await capturarAccionModal(revision, botonAprobar, '4d-pago-modal-final-movil-claro.png')
    await cajeroPage.setViewportSize({ width: 1440, height: 1000 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })

    const aprobacion = cajeroPage.waitForResponse((respuestaPago) => (
      respuestaPago.request().method() === 'POST'
      && new URL(respuestaPago.url()).pathname.endsWith('/aprobar/')
    ))
    await botonAprobar.click()
    expect((await aprobacion).status()).toBe(200)
    await expect(cajeroPage.getByRole('status').filter({ hasText: 'La reserva está confirmada' })).toBeVisible()
    await expect(revision.getByText('Pago revisado', { exact: true })).toBeVisible()
    await expect(revision.getByText('QR', { exact: false })).toHaveCount(0)
    await revision.getByRole('button', { name: 'Cerrar', exact: true }).click()
    await cajeroPage.getByRole('button', { name: 'Reservas', exact: true }).click()
    const ingreso = cajeroPage.getByRole('region', { name: 'Validar ingreso' })
    await expect(ingreso).toBeVisible()
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-escritorio-oscuro.png') })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-escritorio-claro.png') })
    await cajeroPage.setViewportSize({ width: 390, height: 844 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-movil-oscuro.png'), animations: 'disabled' })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-movil-claro.png') })

    await jugadorPage.goto('/mis-reservas')
    const filaReserva = jugadorPage.getByRole('row').filter({ hasText: codigoReserva })
    await expect(filaReserva).toBeVisible()
    await filaReserva.getByRole('button', { name: 'Ver ticket' }).click()
    const ticket = jugadorPage.getByRole('dialog')
    const descargaQr = ticket.getByRole('link', { name: 'Descargar QR' })
    await expect(ticket.getByAltText('Código QR de la reserva confirmada')).toBeVisible()
    await expect(descargaQr).toBeVisible()
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-movil-claro.png') })
    await capturarAccionModal(ticket, descargaQr, '4d-ticket-final-movil-claro.png')
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-movil-oscuro.png'), animations: 'disabled' })
    await capturarAccionModal(ticket, descargaQr, '4d-ticket-final-movil-oscuro.png')
    await jugadorPage.setViewportSize({ width: 1440, height: 1000 })
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-escritorio-oscuro.png') })
    await capturarAccionModal(ticket, descargaQr, '4d-ticket-final-escritorio-oscuro.png')
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ticket.screenshot({ path: path.join(screenshots, '4d-ticket-escritorio-claro.png') })
    await capturarAccionModal(ticket, descargaQr, '4d-ticket-final-escritorio-claro.png')
    await ticket.getByRole('button', { name: 'Cerrar', exact: true }).click()

    horarioControlado = prepararHorarioEnCurso(codigoReserva)
    const qr = horarioControlado.token_qr
    await ingresar(cajeroNortePage, cajeroNorte, '/panel/cajero')
    await cajeroNortePage.getByRole('button', { name: 'Reservas', exact: true }).click()
    const ingresoNorte = cajeroNortePage.getByRole('region', { name: 'Validar ingreso' })
    await prepararEscanerQr(cajeroNortePage, qr)
    const consultaAjena = cajeroNortePage.waitForResponse((respuestaIngreso) => (
      respuestaIngreso.request().method() === 'POST'
      && new URL(respuestaIngreso.url()).pathname === '/api/reservas/administracion/ingreso/consultar/'
    ))
    await ingresoNorte.getByRole('button', { name: 'Abrir cámara' }).click()
    expect((await consultaAjena).status()).toBe(404)
    await expect(ingresoNorte.getByText('No se pudo validar la reserva. Revisa el código, la sede y el horario.')).toBeVisible()

    await prepararEscanerQr(cajeroPage, qr)
    const consulta = cajeroPage.waitForResponse((respuestaIngreso) => (
      respuestaIngreso.request().method() === 'POST'
      && new URL(respuestaIngreso.url()).pathname === '/api/reservas/administracion/ingreso/consultar/'
    ))
    await ingreso.getByRole('button', { name: 'Abrir cámara' }).click()
    expect((await consulta).status()).toBe(200)
    await expect(ingreso.getByText('[DEMO ALTOQUE] Sede A Centro · [DEMO ALTOQUE] Cancha A heredada')).toBeVisible()
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-qr-escritorio-oscuro.png') })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-qr-escritorio-claro.png') })
    await cajeroPage.setViewportSize({ width: 390, height: 844 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-qr-movil-oscuro.png') })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-qr-movil-claro.png') })
    await cajeroPage.setViewportSize({ width: 1440, height: 1000 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    const registro = cajeroPage.waitForResponse((respuestaIngreso) => (
      respuestaIngreso.request().method() === 'POST'
      && new URL(respuestaIngreso.url()).pathname === '/api/reservas/administracion/ingreso/registrar/'
    ))
    await ingreso.getByRole('button', { name: 'Registrar ingreso' }).click()
    expect((await registro).status()).toBe(201)
    await expect(ingreso.getByText('Ingreso registrado.')).toBeVisible()

    const segundoEscaneo = cajeroPage.waitForResponse((respuestaIngreso) => (
      respuestaIngreso.request().method() === 'POST'
      && new URL(respuestaIngreso.url()).pathname === '/api/reservas/administracion/ingreso/consultar/'
    ))
    await ingreso.getByRole('button', { name: 'Abrir cámara' }).click()
    expect((await segundoEscaneo).status()).toBe(200)
    await expect(ingreso.getByText('Ingreso ya registrado', { exact: true })).toBeVisible()
    await expect(ingreso.getByRole('button', { name: 'Registrar ingreso' })).toHaveCount(0)
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-doble-escritorio-oscuro.png') })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-doble-escritorio-claro.png') })
    await cajeroPage.setViewportSize({ width: 390, height: 844 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-doble-movil-oscuro.png') })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-ingreso-doble-movil-claro.png') })
    await cajeroPage.setViewportSize({ width: 1440, height: 1000 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })

    restaurarHorario(codigoReserva, horarioControlado)
    horarioControlado = null
    await filaReserva.getByRole('button', { name: 'Ver detalle' }).click()
    await jugadorPage.getByRole('dialog').getByRole('button', { name: 'Cancelar reserva' }).click()
    const cancelar = jugadorPage.getByRole('dialog')
    await expect(cancelar.getByText('Las cancelaciones voluntarias normalmente no generan devolución del adelanto. Las excepciones y los derechos aplicables pueden requerir revisión de la sede.', { exact: true })).toBeVisible()
    await cancelar.screenshot({ path: path.join(screenshots, '4d-cancelacion-escritorio-claro.png') })
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await cancelar.screenshot({ path: path.join(screenshots, '4d-cancelacion-escritorio-oscuro.png') })
    await jugadorPage.setViewportSize({ width: 390, height: 844 })
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await cancelar.screenshot({ path: path.join(screenshots, '4d-cancelacion-movil-claro.png') })
    await jugadorPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await cancelar.screenshot({ path: path.join(screenshots, '4d-cancelacion-movil-oscuro.png') })
    await cancelar.getByLabel('Motivo de cancelación').fill('Prueba local de cancelación')
    await cancelar.getByRole('button', { name: 'Confirmar cancelación' }).click()
    await expect(jugadorPage.getByRole('status').filter({ hasText: 'Reserva cancelada' })).toBeVisible()
    await expect(filaReserva.getByText('Cancelada')).toBeVisible()

    await prepararEscanerQr(cajeroPage, qr)
    const qrCancelado = cajeroPage.waitForResponse((respuestaIngreso) => (
      respuestaIngreso.request().method() === 'POST'
      && new URL(respuestaIngreso.url()).pathname === '/api/reservas/administracion/ingreso/consultar/'
    ))
    await ingreso.getByRole('button', { name: 'Abrir cámara' }).click()
    expect((await qrCancelado).status()).toBe(400)
    await expect(ingreso.getByText('No se pudo validar la reserva. Revisa el código, la sede y el horario.')).toBeVisible()
    await ingreso.screenshot({ path: path.join(screenshots, '4d-qr-cancelado-escritorio-oscuro.png') })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-qr-cancelado-escritorio-claro.png') })
    await cajeroPage.setViewportSize({ width: 390, height: 844 })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'dark' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-qr-cancelado-movil-oscuro.png') })
    await cajeroPage.evaluate(() => { document.documentElement.dataset.theme = 'light' })
    await ingreso.screenshot({ path: path.join(screenshots, '4d-qr-cancelado-movil-claro.png') })

  } finally {
    if (horarioControlado) restaurarHorario(codigoReserva, horarioControlado)
    await contextoJugador.close()
    await contextoCajero.close()
    await contextoCajeroNorte.close()
  }
})
