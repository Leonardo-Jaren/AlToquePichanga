import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import api from '@/shared/services/api'
import CalendarioOperativo from '@/modules/calendario/components/calendario/CalendarioOperativo.vue'
import CalendarioAdminPanel from '@/modules/calendario/components/paneles/CalendarioAdminPanel.vue'
import CanchasPublicasView from '@/modules/calendario/views/CanchasPublicasView.vue'
import FormularioCancha from '@/modules/canchas/components/FormularioCancha.vue'
import { horariosApi } from '@/modules/horarios/services/horarios'
import { tarifasApi } from '@/modules/tarifas/services/tarifas'
import { inicioSemana, rangoCalendario } from '@/modules/calendario/utils/fechas'

vi.mock('@/shared/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

const fecha = '2026-10-23'
const bloques = [
  { fecha_inicio: `${fecha}T18:00:00-05:00`, fecha_fin: `${fecha}T19:00:00-05:00`, estado: 'operativa', habilitada_operativamente: true, considera_reservas: false, origen: 'horario_semanal', precio: '50.00', tipo_tarifa: 'diurna', moneda: 'PEN', tarifa_estado: 'configurada' },
  { fecha_inicio: `${fecha}T19:00:00-05:00`, fecha_fin: `${fecha}T20:00:00-05:00`, estado: 'operativa', habilitada_operativamente: true, considera_reservas: false, origen: 'horario_semanal', precio: '70.00', tipo_tarifa: 'nocturna', moneda: 'PEN', tarifa_estado: 'configurada' },
  { fecha_inicio: `${fecha}T20:00:00-05:00`, fecha_fin: `${fecha}T21:00:00-05:00`, estado: 'cerrada', habilitada_operativamente: false, considera_reservas: false, origen: 'horario_semanal', motivo: 'Cierre temporal.', precio: null, tarifa_estado: 'no_disponible' },
  { fecha_inicio: `${fecha}T21:00:00-05:00`, fecha_fin: `${fecha}T22:00:00-05:00`, estado: 'operativa', habilitada_operativamente: true, considera_reservas: false, origen: 'ampliacion_excepcional', precio: null, tarifa_estado: 'sin_configurar' },
]
const cancha = {
  id: 21, nombre: 'Cancha Centro', modalidad: 7, tipo_superficie: 'Sintético',
  descripcion: 'Cancha demostrativa', capacidad_jugadores: 14, techada: false, iluminacion: true,
  caracteristicas: ['Vestuarios'], estado: 'activa', imagen_principal_url: null,
  sede: { nombre: 'Sede Centro', distrito: 'Huánuco', provincia: 'Huánuco', departamento: 'Huánuco' },
}
const cotizacion = {
  fecha, hora_inicio: `${fecha}T18:00:00-05:00`, hora_fin: `${fecha}T20:00:00-05:00`,
  duracion_horas: 2, bloques: bloques.slice(0, 2).map((bloque) => ({ ...bloque, nombre_tarifa: bloque.tipo_tarifa })),
  subtotal: '120.00', total: '120.00', moneda: 'PEN',
}

function respuestaDisponibilidad(consideraReservas = false) {
  return { data: {
    considera_reservas: consideraReservas,
    zona_horaria: 'America/Lima',
    bloques: bloques.map((bloque) => ({
      ...bloque,
      ...(consideraReservas ? {
        reservable: bloque.habilitada_operativamente && bloque.tarifa_estado === 'configurada',
      } : {}),
    })),
  } }
}
function resolverGet(url) {
  if (url === '/publico/canchas/') return Promise.resolve({ data: [{ ...cancha }] })
  if (url === '/auth/perfil/') return Promise.reject({ response: { status: 401 } })
  if (url.startsWith('/publico/canchas/')) return Promise.resolve(respuestaDisponibilidad(true))
  if (url.startsWith('/reservas/administracion/disponibilidad/')) return Promise.resolve(respuestaDisponibilidad(true))
  if (url === '/sedes/') return Promise.resolve({ data: [{ id: 3, nombre: 'Sede Centro' }] })
  if (url === '/canchas/') return Promise.resolve({ data: { results: [
    { id: 21, nombre: cancha.nombre, estado: 'activa', sede_id: 3 },
    { id: 22, nombre: 'Cancha Norte', estado: 'activa', sede_id: 3 },
  ] } })
  return Promise.resolve(respuestaDisponibilidad())
}
const stubs = {
  RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
  ThemeSelector: { template: '<span aria-label="Selector de tema" />' },
}

beforeEach(() => {
  vi.resetAllMocks()
  api.get.mockImplementation(resolverGet)
  api.post.mockResolvedValue({ data: cotizacion })
  api.patch.mockResolvedValue({ data: {} })
})

describe('calendario de la Fase 3D', () => {
  it('cambia entre vistas y navega usando semanas de lunes a domingo', async () => {
    expect(inicioSemana(fecha)).toBe('2026-10-19')
    expect(rangoCalendario('semana', fecha)).toEqual({ desde: '2026-10-19', hasta: '2026-10-25' })
    const wrapper = mount(CalendarioOperativo, { props: { cancha }, global: { plugins: [createPinia()], stubs } })
    await flushPromises()
    await wrapper.get('input[type="date"]').setValue(fecha)
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('/canchas/21/disponibilidad-operativa/', {
      params: { desde: fecha, hasta: fecha },
    })
    await wrapper.get('button[aria-pressed="false"]').trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('/canchas/21/disponibilidad-operativa/', {
      params: { desde: '2026-10-19', hasta: '2026-10-25' },
    })
    await wrapper.get('button[aria-label="Periodo siguiente"]').trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('/canchas/21/disponibilidad-operativa/', {
      params: { desde: '2026-10-26', hasta: '2026-11-01' },
    })
    wrapper.unmount()
  })

  it('presenta precios, cierres y ampliaciones; solo une bloques operativos consecutivos', async () => {
    const wrapper = mount(CalendarioOperativo, { props: { cancha }, global: { plugins: [createPinia()], stubs } })
    await flushPromises()
    await wrapper.get('input[type="date"]').setValue(fecha)
    await flushPromises()
    expect(wrapper.text()).toContain('S/ 50.00')
    expect(wrapper.text()).toContain('Cerrado')
    expect(wrapper.text()).toContain('Tarifa no configurada')
    expect(wrapper.text()).toContain('Ampliación excepcional')
    expect(wrapper.text()).toContain('no considera reservas de jugadores')

    const agregar = wrapper.findAll('button').filter((boton) => boton.text() === 'Agregar a cotización')
    expect(agregar).toHaveLength(2)
    await agregar[0].trigger('click')
    const siguiente = wrapper.findAll('button').filter((boton) => boton.text() === 'Agregar a cotización')[0]
    await siguiente.trigger('click')
    expect(wrapper.text()).toContain('2 bloques consecutivos seleccionados')
    await wrapper.findAll('button').find((boton) => boton.text().includes('Cotizar selección')).trigger('click')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/canchas/21/calcular-precio/', {
      fecha, hora_inicio: '18:00', duracion_horas: 2,
    })
    expect(wrapper.text()).toContain('S/ 120.00')

    const bloqueCerrado = wrapper.findAll('article').find((item) => (
      item.text().includes('20:00–21:00') && item.findAll('button').length === 1
    ))
    await bloqueCerrado.find('button').trigger('click')
    expect(wrapper.text()).toContain('Cierre temporal.')
    expect(bloqueCerrado.text()).not.toContain('Agregar a cotización')
    wrapper.unmount()
  })

  it('consulta la API pública, mantiene la vista informativa y no muestra datos privados', async () => {
    const wrapper = mount(CanchasPublicasView, { global: { plugins: [createPinia()], stubs } })
    await flushPromises()
    expect(api.get).toHaveBeenCalledWith('/publico/canchas/')
    expect(wrapper.text()).toContain('Horarios operativos y precios por cancha')
    expect(wrapper.text()).toContain('Sede Centro')
    expect(wrapper.text()).toContain('retenciones temporales vigentes')
    expect(wrapper.text()).not.toContain('teléfono')
    await wrapper.get('input[type="date"]').setValue(fecha)
    await flushPromises()
    expect(api.get).toHaveBeenCalledWith('/publico/canchas/21/disponibilidad/', {
      params: { desde: fecha, hasta: fecha },
    })
    wrapper.unmount()
  })

  it('muestra la matriz administrativa de todas las canchas de la sede con disponibilidad real', async () => {
    const wrapper = mount(CalendarioAdminPanel, {
      props: { sedes: [{ id: 3, nombre: 'Sede Centro' }], sedeInicialId: 3, sedeFija: true },
      global: { plugins: [createPinia()], stubs },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Sede autorizada')
    await wrapper.get('input[type="date"]').setValue(fecha)
    await flushPromises()
    expect(wrapper.text()).toContain('Cancha Centro')
    expect(wrapper.text()).toContain('Cancha Norte')
    expect(api.get).toHaveBeenCalledWith('/canchas/', { params: { sede: '3', page_size: 100 } })
    expect(api.get).toHaveBeenCalledWith('/reservas/administracion/disponibilidad/21/', {
      params: { desde: fecha, hasta: fecha },
    })
    expect(api.get).toHaveBeenCalledWith('/reservas/administracion/disponibilidad/22/', {
      params: { desde: fecha, hasta: fecha },
    })
    wrapper.unmount()
  })

  it('permite publicar una cancha desde su formulario con una decisión explícita', async () => {
    const wrapper = mount(FormularioCancha, {
      props: { sedes: [{ id: 3, nombre: 'Sede Centro' }], sedeInicialId: 3 },
    })
    await wrapper.get('#cancha-nombre').setValue('Cancha Centro')
    await wrapper.get('#cancha-modalidad').setValue('7')
    await wrapper.get('#cancha-tipo_superficie').setValue('Sintético')
    await wrapper.findAll('input[type="checkbox"]')[2].setValue(true)
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('guardar')[0][0].datos).toMatchObject({ publicada: true, sede_id: 3 })
    wrapper.unmount()
  })

  it('muestra el error de consulta y conserva los tokens de modo claro y oscuro', async () => {
    api.get.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'No tienes acceso a esta cancha.' } } })
    const wrapper = mount(CalendarioOperativo, { props: { cancha }, global: { plugins: [createPinia()], stubs } })
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toBe('No tienes acceso a esta cancha.')
    const tokens = readFileSync(resolve(import.meta.dirname, '../src/shared/styles/tokens.css'), 'utf8')
    expect(tokens).toContain("data-theme='dark'")
    expect(tokens).toContain('#C0FA04')
    wrapper.unmount()
  })
})

describe('servicios integrados', () => {
  it('usa las rutas públicas sin reemplazar los servicios protegidos', async () => {
    await horariosApi.disponibilidadPublica(21, fecha, fecha)
    await tarifasApi.cotizarPublico(21, { fecha, hora_inicio: '18:00', duracion_horas: 2 })
    expect(api.get).toHaveBeenCalledWith('/publico/canchas/21/disponibilidad/', {
      params: { desde: fecha, hasta: fecha },
    })
    expect(api.post).toHaveBeenCalledWith('/publico/canchas/21/cotizar/', {
      fecha, hora_inicio: '18:00', duracion_horas: 2,
    })
  })
})
