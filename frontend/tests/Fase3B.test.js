import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import api from '@/shared/services/api'
import GestionHorariosPanel from '@/modules/horarios/components/GestionHorariosPanel.vue'
import ExcepcionesPanel from '@/modules/horarios/components/ExcepcionesPanel.vue'
import DisponibilidadOperativa from '@/modules/horarios/components/DisponibilidadOperativa.vue'
import { horariosApi } from '@/modules/horarios/services/horarios'
import { fechaHoraLima, validarIntervalos, validarIntervalosDentroDeMarco, diasEntre } from '@/modules/horarios/utils/horarios'

vi.mock('@/shared/services/api', () => ({
  default: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
}))

const sede = { id: 3, nombre: 'Complejo Amarilis' }
const cancha = { id: 21, sede_id: 3, nombre: 'Cancha 1' }
const horasSede = [
  ...[0, 1, 2, 3, 4].map((dia_semana) => ({ dia_semana, hora_apertura: '08:00', hora_cierre: '23:00' })),
  { dia_semana: 5, hora_apertura: '08:00', hora_cierre: '00:00' },
  { dia_semana: 6, hora_apertura: '09:00', hora_cierre: '22:00' },
]

function respuestaHorarioCancha(datos = {}) {
  return { data: { cancha_id: 21, sede_id: 3, configurado: true, hereda_horario_sede: true, dias_heredados: [], intervalos: [], intervalos_efectivos: horasSede, ...datos } }
}

beforeEach(() => {
  vi.resetAllMocks()
  window.confirm = vi.fn(() => true)
  api.get.mockImplementation((url) => {
    if (url === '/sedes/3/horario-semanal/') return Promise.resolve({ data: { sede_id: 3, configurado: true, zona_horaria: 'America/Lima', intervalos: horasSede } })
    if (url === '/canchas/') return Promise.resolve({ data: { count: 1, results: [cancha] } })
    if (url === '/canchas/21/horario-semanal/') return Promise.resolve(respuestaHorarioCancha())
    if (url === '/horarios/excepciones/') return Promise.resolve({ data: { count: 0, results: [] } })
    if (url === '/canchas/21/disponibilidad-operativa/') return Promise.resolve({ data: { bloques: [] } })
    return Promise.resolve({ data: [] })
  })
  api.put.mockImplementation((_url, datos) => Promise.resolve({ data: { configurado: true, ...datos, intervalos_efectivos: datos.intervalos } }))
  api.post.mockResolvedValue({ data: {} })
})

describe('reglas y servicio de horarios', () => {
  it('usa los endpoints de semana y conserva el offset de Lima en excepciones', async () => {
    await horariosApi.guardarHorarioSede(3, { intervalos: horasSede })
    expect(api.put).toHaveBeenCalledWith('/sedes/3/horario-semanal/', { intervalos: horasSede })
    expect(fechaHoraLima('2026-10-18', '08:30')).toBe('2026-10-18T08:30:00-05:00')
  })

  it('detecta superposición y permite un cierre al día siguiente', () => {
    expect(validarIntervalos([
      { dia_semana: 0, hora_apertura: '08:00', hora_cierre: '12:00' },
      { dia_semana: 0, hora_apertura: '11:00', hora_cierre: '14:00' },
    ])).toContain('superponerse')
    expect(validarIntervalos([
      { dia_semana: 4, hora_apertura: '20:00', hora_cierre: '02:00' },
      { dia_semana: 5, hora_apertura: '02:00', hora_cierre: '06:00' },
    ])).toBe('')
    expect(diasEntre('2026-10-01', '2026-10-31')).toBe(30)
  })

  it('mantiene el horario particular de cancha dentro del marco de la sede', () => {
    expect(validarIntervalosDentroDeMarco([
      { dia_semana: 0, hora_apertura: '07:00', hora_cierre: '09:00' },
    ], horasSede)).toContain('dentro del horario de sede')
    expect(validarIntervalosDentroDeMarco([
      { dia_semana: 0, hora_apertura: '16:00', hora_cierre: '23:00' },
    ], horasSede)).toBe('')
  })
})

describe('administración y consulta de horarios', () => {
  it('permite heredar días concretos y guarda el resto como horario propio', async () => {
    const wrapper = mount(GestionHorariosPanel, { props: { sedes: [sede], sedeInicialId: 3, sedeFija: true } })
    await flushPromises()
    for (const dia of ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']) {
      await wrapper.get(`button[aria-label="Personalizar ${dia}"]`).trigger('click')
    }
    await wrapper.findAll('button').find((item) => item.text() === 'Guardar horario de cancha').trigger('click')
    await flushPromises()
    expect(api.put).toHaveBeenLastCalledWith('/canchas/21/horario-semanal/', expect.objectContaining({
      hereda_horario_sede: false,
      dias_heredados: [5, 6],
      intervalos: horasSede.slice(0, 5),
    }))
    expect(wrapper.text()).toContain('Carril heredado de sede')
    wrapper.unmount()
  })

  it('envía las fechas y el motivo de una excepción con UTC−05:00', async () => {
    const wrapper = mount(ExcepcionesPanel, { props: { sedeId: 3, canchas: [cancha] } })
    await flushPromises()
    await wrapper.get('button').trigger('click')
    await wrapper.get('input[placeholder*="Mantenimiento"]').setValue('Reparación de luminarias')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/horarios/excepciones/', expect.objectContaining({
      sede_id: 3, tipo: 'cierre', fecha_inicio: expect.stringMatching(/-05:00$/),
      fecha_fin: expect.stringMatching(/-05:00$/), motivo: 'Reparación de luminarias',
    }))
    expect(api.get).toHaveBeenCalledWith('/horarios/excepciones/', { params: expect.objectContaining({ sede: 3, desde: expect.stringMatching(/^\d{4}-\d{2}-\d{2}$/) }) })
    wrapper.unmount()
  })

  it('no permite guardar una excepción cuyo final precede al inicio', async () => {
    const wrapper = mount(ExcepcionesPanel, { props: { sedeId: 3, canchas: [cancha] } })
    await flushPromises()
    await wrapper.get('button').trigger('click')
    const fechas = wrapper.findAll('input[type="date"]')
    const horas = wrapper.findAll('input[type="time"]')
    await fechas[0].setValue('2026-10-18')
    await fechas[1].setValue('2026-10-18')
    await horas[0].setValue('16:00')
    await horas[1].setValue('12:00')
    await wrapper.get('input[placeholder*="Mantenimiento"]').setValue('Reparación')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.text()).toContain('El final debe ocurrir después del inicio.')
    expect(api.post).not.toHaveBeenCalled()
    wrapper.unmount()
  })

  it('oculta acciones de edición al cajero y mantiene su vista de consulta', async () => {
    const wrapper = mount(GestionHorariosPanel, { props: { sedes: [sede], sedeInicialId: 3, sedeFija: true, soloLectura: true } })
    await flushPromises()
    expect(wrapper.text()).toContain('Heredado de sede')
    expect(wrapper.text()).not.toContain('Guardar horario de sede')
    expect(wrapper.text()).not.toContain('Guardar horario de cancha')
    expect(wrapper.findAll('button').some((button) => button.text().includes('Personalizar día'))).toBe(false)
    wrapper.unmount()
  })

  it('marca el resultado como operativo y nunca como disponibilidad para reservar', async () => {
    const wrapper = mount(DisponibilidadOperativa, { props: { canchaId: 21 } })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('No consulta reservas')
    expect(wrapper.text()).not.toContain('Reservar')
    expect(api.get).toHaveBeenCalledWith('/canchas/21/disponibilidad-operativa/', expect.objectContaining({ params: expect.any(Object) }))
    wrapper.unmount()
  })

  it('limita la consulta operativa a 31 días inclusive', async () => {
    const wrapper = mount(DisponibilidadOperativa, { props: { canchaId: 21 } })
    const fechas = wrapper.findAll('input[type="date"]')
    await fechas[0].setValue('2026-10-01')
    await fechas[1].setValue('2026-11-01')
    expect(wrapper.text()).toContain('máximo 31 días')
    expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    await wrapper.find('form').trigger('submit')
    expect(api.get).not.toHaveBeenCalledWith('/canchas/21/disponibilidad-operativa/', expect.anything())
    wrapper.unmount()
  })
})
