import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, getActivePinia, setActivePinia } from 'pinia'
import api from '@/shared/services/api'
import { useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'
import { reservasApi } from '@/modules/reservas/services/reservas'
import { calcularAdelantoMinimo, formatoCuentaRegresiva, segundosRestantes } from '@/modules/reservas/utils/reservas'
import SolicitudRetencionModal from '@/modules/reservas/components/SolicitudRetencionModal.vue'
import MisReservasView from '@/modules/reservas/views/MisReservasView.vue'
import CalendarioOperativo from '@/modules/calendario/components/calendario/CalendarioOperativo.vue'

vi.mock('@/shared/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

const fecha = '2026-10-26'
const cancha = { id: 41, nombre: 'Cancha Centro' }
const seleccion = [{
  fecha_inicio: `${fecha}T18:00:00-05:00`,
  fecha_fin: `${fecha}T19:00:00-05:00`,
}]
const cotizacion = { total: '101.01', moneda: 'PEN' }
const reserva = {
  codigo: 'ATP-AB12CD34EF56', cancha_id: 41, cancha_nombre: cancha.nombre,
  sede_nombre: 'Sede Centro', inicio: `${fecha}T18:00:00-05:00`,
  fin: `${fecha}T19:00:00-05:00`, duracion_horas: 1,
  importe_total: '101.01', adelanto_minimo: '50.51', moneda: 'PEN',
  estado: 'retenida', retencion_vence_en: new Date(Date.now() + 120000).toISOString(),
  cotizacion_aplicada: { bloques: [{
    fecha_inicio: `${fecha}T18:00:00-05:00`, fecha_fin: `${fecha}T19:00:00-05:00`,
    nombre_tarifa: 'Nocturna', precio: '101.01', moneda: 'PEN',
  }] },
}

const stubs = {
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  ModalBase: {
    props: ['modelValue', 'titulo'],
    emits: ['update:modelValue'],
    template: '<div v-if="modelValue" role="dialog"><h2>{{ titulo }}</h2><slot /><footer><slot name="pie" /></footer></div>',
  },
  ThemeSelector: { template: '<span aria-label="Selector de tema" />' },
}

const sockets = []
class WebSocketPrueba {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3
  constructor(url) { this.url = url; this.readyState = 0; sockets.push(this) }
  open() { this.readyState = 1; this.onopen?.({}) }
  enviar(datos) { this.onmessage?.({ data: JSON.stringify(datos) }) }
  close(codigo = 1000) { this.readyState = 3; this.onclose?.({ code: codigo }) }
}

function montar(componente, props = {}) {
  return mount(componente, {
    props,
    global: { plugins: [getActivePinia() || createPinia()], stubs },
  })
}

beforeEach(() => {
  vi.resetAllMocks()
  setActivePinia(createPinia())
})

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  sockets.length = 0
})

describe('Fase 4A: retenciones de reserva', () => {
  it('calcula el adelanto al centavo y el tiempo restante', () => {
    expect(calcularAdelantoMinimo('101.01')).toBe('50.51')
    expect(calcularAdelantoMinimo('50.00')).toBe('25.00')
    expect(segundosRestantes('2026-10-26T00:00:00Z', Date.parse('2026-10-25T23:59:00Z'))).toBe(60)
    expect(formatoCuentaRegresiva(3661)).toBe('01:01:01')
  })

  it('solicita la retención con una clave idempotente y muestra el resultado del servidor', async () => {
    const auth = useAutenticacionStore()
    auth.usuario = { id: 7, es_jugador: true, membresias: [] }
    vi.spyOn(reservasApi, 'solicitar').mockResolvedValue({ data: reserva })
    const wrapper = montar(SolicitudRetencionModal, {
      modelValue: true, cancha, seleccion, cotizacion,
    })

    expect(wrapper.text()).toContain('Adelanto mínimo (50%)')
    expect(wrapper.text()).toContain('S/ 50.51')
    await wrapper.findAll('button').find((boton) => boton.text().includes('Apartar horario')).trigger('click')
    await flushPromises()

    expect(reservasApi.solicitar).toHaveBeenCalledWith(expect.objectContaining({
      cancha_id: cancha.id, fecha, hora_inicio: '18:00', duracion_horas: 1,
      clave_idempotencia: expect.stringMatching(/^[0-9a-f-]{36}$/i),
    }))
    expect(wrapper.text()).toContain(reserva.codigo)
    expect(wrapper.text()).toContain('Horario retenido temporalmente')
    expect(wrapper.emitted('reservada')).toHaveLength(1)
    wrapper.unmount()
  })

  it('mantiene el estado de carga y evita solicitudes duplicadas por clics repetidos', async () => {
    const auth = useAutenticacionStore()
    auth.usuario = { id: 7, es_jugador: true, membresias: [] }
    let resolver
    vi.spyOn(reservasApi, 'solicitar').mockImplementation(() => new Promise((resolve) => {
      resolver = resolve
    }))
    const wrapper = montar(SolicitudRetencionModal, {
      modelValue: true, cancha, seleccion, cotizacion,
    })
    const apartar = wrapper.findAll('button').find((boton) => boton.text().includes('Apartar horario'))

    await apartar.trigger('click')
    await apartar.trigger('click')

    expect(reservasApi.solicitar).toHaveBeenCalledTimes(1)
    expect(wrapper.get('button[aria-busy="true"]').element.disabled).toBe(true)
    resolver({ data: reserva })
    await flushPromises()
    expect(wrapper.text()).toContain(reserva.codigo)
    wrapper.unmount()
  })

  it('informa conflicto y manda a actualizar la disponibilidad', async () => {
    const auth = useAutenticacionStore()
    auth.usuario = { id: 8, es_jugador: true, membresias: [] }
    vi.spyOn(reservasApi, 'solicitar').mockRejectedValue({ response: { status: 409 } })
    const wrapper = montar(SolicitudRetencionModal, {
      modelValue: true, cancha, seleccion, cotizacion,
    })

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Ese horario acaba de ocuparse')
    expect(wrapper.emitted('conflicto')).toHaveLength(1)
    wrapper.unmount()
  })

  it('refresca el calendario público y deja visible el conflicto al competir por un horario', async () => {
    const auth = useAutenticacionStore()
    auth.usuario = { id: 8, es_jugador: true, membresias: [] }
    let consultas = 0
    api.get.mockImplementation((url) => {
      if (!url.includes('/disponibilidad/')) return Promise.resolve({ data: [] })
      consultas += 1
      const ocupado = consultas >= 3
      return Promise.resolve({ data: {
        considera_reservas: true,
        zona_horaria: 'America/Lima',
        bloques: [{
          fecha_inicio: seleccion[0].fecha_inicio,
          fecha_fin: seleccion[0].fecha_fin,
          estado: ocupado ? 'retenida' : 'operativa',
          estado_reserva: ocupado ? 'retenida' : null,
          habilitada_operativamente: !ocupado,
          reservable: !ocupado,
          precio: '101.01', moneda: 'PEN', tarifa_estado: 'configurada',
        }],
      } })
    })
    api.post.mockImplementation((url) => {
      if (url.includes('/cotizar/')) return Promise.resolve({ data: cotizacion })
      return Promise.reject({ response: { status: 409 } })
    })
    const wrapper = montar(CalendarioOperativo, { cancha, publico: true })
    await flushPromises()
    await wrapper.get('input[type="date"]').setValue(fecha)
    await flushPromises()
    await wrapper.findAll('button').find((boton) => boton.text().includes('Seleccionar horario')).trigger('click')
    await wrapper.findAll('button').find((boton) => boton.text().includes('Calcular importe')).trigger('click')
    await flushPromises()
    await wrapper.findAll('button').find((boton) => boton.text().includes('Solicitar reserva temporal')).trigger('click')
    await wrapper.findAll('button').find((boton) => boton.text().includes('Apartar horario')).trigger('click')
    await flushPromises()

    expect(consultas).toBe(3)
    expect(wrapper.get('[role="alert"]').text()).toContain('El calendario se actualizó')
    expect(wrapper.text()).toContain('Retenida temporalmente')
    expect(wrapper.text()).not.toContain('Horario por solicitar')
    wrapper.unmount()
  })

  it('sincroniza por REST tras un evento y avisa al invalidar el bloque seleccionado', async () => {
    vi.stubGlobal('WebSocket', WebSocketPrueba)
    let ocupado = false
    let consultas = 0
    api.get.mockImplementation((url) => {
      if (!url.includes('/disponibilidad/')) return Promise.resolve({ data: [] })
      consultas += 1
      return Promise.resolve({ data: {
        considera_reservas: true,
        zona_horaria: 'America/Lima',
        bloques: [{
          fecha_inicio: seleccion[0].fecha_inicio,
          fecha_fin: seleccion[0].fecha_fin,
          estado: ocupado ? 'retenida' : 'operativa',
          estado_reserva: ocupado ? 'retenida' : null,
          habilitada_operativamente: !ocupado,
          reservable: !ocupado,
          precio: '101.01', moneda: 'PEN', tarifa_estado: 'configurada',
        }],
      } })
    })
    api.post.mockResolvedValue({ data: cotizacion })

    const wrapper = montar(CalendarioOperativo, { cancha, publico: true })
    await flushPromises()
    await wrapper.get('input[type="date"]').setValue(fecha)
    await flushPromises()
    const socket = sockets.at(-1)
    socket.open()
    await wrapper.findAll('button').find((boton) => boton.text().includes('Seleccionar horario')).trigger('click')
    expect(wrapper.text()).toContain('1 bloque seleccionado')

    ocupado = true
    socket.enviar({
      tipo: 'disponibilidad_actualizada', cancha_id: cancha.id,
      fecha, motivo: 'retencion_creada',
    })
    await flushPromises()

    expect(consultas).toBe(3)
    expect(wrapper.text()).toContain('Retenida temporalmente')
    expect(wrapper.get('[role="alert"]').text()).toContain('dejó de estar disponible')
    expect(wrapper.text()).not.toContain('1 bloque seleccionado')
    wrapper.unmount()
  })

  it('explica cuando la sesión vence durante la solicitud', async () => {
    const auth = useAutenticacionStore()
    auth.usuario = { id: 9, es_jugador: true, membresias: [] }
    vi.spyOn(reservasApi, 'solicitar').mockRejectedValue({ response: { status: 401 } })
    const wrapper = montar(SolicitudRetencionModal, {
      modelValue: true, cancha, seleccion, cotizacion,
    })

    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(wrapper.get('[role="alert"]').text()).toContain('Tu sesión venció')
    wrapper.unmount()
  })

  it('no envía una solicitud si la sesión no está autenticada', async () => {
    vi.spyOn(reservasApi, 'solicitar').mockResolvedValue({ data: reserva })
    const wrapper = montar(SolicitudRetencionModal, {
      modelValue: true, cancha, seleccion, cotizacion,
    })

    expect(wrapper.text()).toContain('inicia sesión')
    expect(wrapper.get('button[disabled]').exists()).toBe(true)
    expect(reservasApi.solicitar).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('lista reservas propias y confirma la cancelación de una retención', async () => {
    vi.spyOn(reservasApi, 'listarPropias')
      .mockResolvedValueOnce({ data: { count: 1, results: [reserva] } })
      .mockResolvedValueOnce({ data: { count: 0, results: [] } })
    vi.spyOn(reservasApi, 'obtenerPropia').mockResolvedValue({ data: reserva })
    vi.spyOn(reservasApi, 'cancelar').mockResolvedValue({ data: { ...reserva, estado: 'cancelada' } })
    const wrapper = montar(MisReservasView)
    await flushPromises()

    expect(wrapper.text()).toContain(reserva.codigo)
    await wrapper.findAll('button').find((boton) => boton.text().includes('Ver detalle')).trigger('click')
    await flushPromises()
    expect(reservasApi.obtenerPropia).toHaveBeenCalledWith(reserva.codigo)
    await wrapper.findAll('button').find((boton) => boton.text().includes('Cancelar retención')).trigger('click')
    await wrapper.findAll('button').find((boton) => boton.text().includes('Sí, cancelar')).trigger('click')
    await flushPromises()

    expect(reservasApi.cancelar).toHaveBeenCalledWith(reserva.codigo)
    expect(wrapper.text()).toContain('La retención se canceló y el horario quedó libre.')
    expect(wrapper.text()).toContain('Cancelada')
    wrapper.unmount()
  })
})
