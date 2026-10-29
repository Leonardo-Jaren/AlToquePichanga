import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import api from '@/shared/services/api'
import SelectControl from '@/shared/components/controles/SelectControl.vue'
import TarifaForm from '@/modules/tarifas/components/formularios/TarifaForm.vue'
import ReglasTarifa from '@/modules/tarifas/components/listados/ReglasTarifa.vue'
import DisponibilidadTarifada from '@/modules/tarifas/components/precios/DisponibilidadTarifada.vue'
import GestionTarifasPanel from '@/modules/tarifas/components/paneles/GestionTarifasPanel.vue'
import { tarifasApi } from '@/modules/tarifas/services/tarifas'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'

vi.mock('@/shared/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

const bloques = [
  { fecha_inicio: '2026-10-23T18:00:00-05:00', fecha_fin: '2026-10-23T19:00:00-05:00', estado: 'operativa', habilitada_operativamente: true, considera_reservas: false, precio: '50.00', tipo_tarifa: 'diurna', moneda: 'PEN', tarifa_estado: 'configurada' },
  { fecha_inicio: '2026-10-23T19:00:00-05:00', fecha_fin: '2026-10-23T20:00:00-05:00', estado: 'operativa', habilitada_operativamente: true, considera_reservas: false, precio: '70.00', tipo_tarifa: 'nocturna', moneda: 'PEN', tarifa_estado: 'configurada' },
  { fecha_inicio: '2026-10-23T20:00:00-05:00', fecha_fin: '2026-10-23T21:00:00-05:00', estado: 'cerrada', habilitada_operativamente: false, considera_reservas: false, motivo: 'Mantenimiento', precio: null, tarifa_estado: 'no_disponible' },
]

beforeEach(() => {
  vi.resetAllMocks()
  window.confirm = vi.fn(() => true)
  api.get.mockResolvedValue({ data: { considera_reservas: false, bloques } })
  api.post.mockResolvedValue({ data: {
    fecha: '2026-10-23', hora_inicio: '2026-10-23T18:00:00-05:00', hora_fin: '2026-10-23T20:00:00-05:00',
    duracion_horas: 2, bloques: bloques.slice(0, 2).map((bloque) => ({ ...bloque, nombre_tarifa: bloque.tipo_tarifa })),
    subtotal: '120.00', total: '120.00', moneda: 'PEN',
  } })
  api.patch.mockResolvedValue({ data: {} })
})

describe('componentes reutilizables de tarifas', () => {
  it('mantiene un selector etiquetado, con objetivo accesible y errores asociados', async () => {
    const wrapper = mount(SelectControl, { props: {
      id: 'sede', label: 'Sede', modelValue: '3', error: 'Selecciona una sede válida.',
      options: [{ value: '3', label: 'Complejo Centro' }],
    } })
    expect(wrapper.get('label').attributes('for')).toBe('sede')
    expect(wrapper.get('select').attributes('aria-describedby')).toBe('sede-error')
    expect(wrapper.get('select').attributes('aria-invalid')).toBe('true')
    await wrapper.get('select').setValue('3')
    expect(wrapper.emitted('update:modelValue')).toEqual([['3']])
    wrapper.unmount()
  })

  it('valida y envía una regla sin convertir dinero a punto flotante', async () => {
    const wrapper = mount(TarifaForm)
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
    const inputsHora = wrapper.findAll('input[type="time"]')
    await inputsHora[0].setValue('08:00')
    await inputsHora[1].setValue('18:00')
    await wrapper.get('input[inputmode="decimal"]').setValue('50,25')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('guardar')[0][0]).toMatchObject({
      tipo: 'diurna', dias_semana: [0, 1, 2, 3, 4], hora_inicio: '08:00',
      hora_fin: '18:00', precio_hora: '50.25', moneda: 'PEN',
    })
    wrapper.unmount()
  })

  it('muestra el listado con precios PEN y respeta el modo de solo lectura', async () => {
    const regla = { id: 4, tipo: 'nocturna', nombre: 'Noche', dias_semana: [4], hora_inicio: '18:00', hora_fin: '23:00', vigente_desde: '2026-01-01', vigente_hasta: null, precio_hora: '70.00', moneda: 'PEN', activa: true }
    const wrapper = mount(ReglasTarifa, { props: { reglas: [regla], soloLectura: true } })
    expect(wrapper.text()).toContain('S/ 70.00')
    expect(wrapper.text()).toContain('Viernes')
    expect(wrapper.text()).not.toContain('Editar')
    expect(wrapper.text()).not.toContain('Desactivar')
    wrapper.unmount()
  })

  it('edita y desactiva una regla desde el panel administrativo con confirmación', async () => {
    const regla = { id: 4, cancha_id: 21, tipo: 'diurna', nombre: 'Día', dias_semana: [0, 1, 2, 3, 4], fecha_aplicable_desde: null, fecha_aplicable_hasta: null, hora_inicio: '08:00', hora_fin: '18:00', todo_el_dia: false, vigente_desde: '2026-01-01', vigente_hasta: null, precio_hora: '50.00', moneda: 'PEN', activa: true }
    api.get.mockImplementation((url) => {
      if (url === '/canchas/') return Promise.resolve({ data: { results: [{ id: 21, sede_id: 3, nombre: 'Cancha 1' }] } })
      if (url === '/canchas/21/tarifas/') return Promise.resolve({ data: { resultados: [regla] } })
      return Promise.resolve({ data: { bloques: [] } })
    })
    const wrapper = mount(GestionTarifasPanel, { props: { sedes: [{ id: 3, nombre: 'A Centro' }], sedeInicialId: 3, sedeFija: true } })
    await flushPromises()
    expect(wrapper.text()).toContain('S/ 50.00')
    await wrapper.findAll('button').find((button) => button.text() === 'Editar').trigger('click')
    await wrapper.get('input[inputmode="decimal"]').setValue('72.50')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/canchas/21/tarifas/4/', expect.objectContaining({ precio_hora: '72.50' }))
    await wrapper.findAll('button').find((button) => button.text() === 'Desactivar').trigger('click')
    await flushPromises()
    expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining('Se conservará en el historial'))
    expect(api.post).toHaveBeenCalledWith('/canchas/21/tarifas/4/estado/', { activa: false, confirmar: true })
    wrapper.unmount()
  })

  it('consulta bloques, distingue cierres y presenta el total calculado por el servidor', async () => {
    const wrapper = mount(DisponibilidadTarifada, { props: { canchaId: 21 } })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.get).toHaveBeenCalledWith('/canchas/21/disponibilidad-operativa/', { params: expect.objectContaining({ desde: expect.any(String), hasta: expect.any(String) }) })
    expect(wrapper.text()).toContain('S/ 50.00')
    expect(wrapper.text()).toContain('Cerrado · no se muestra precio')
    expect(wrapper.text()).toContain('No consulta reservas')
    const forms = wrapper.findAll('form')
    await forms.at(-1).trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/canchas/21/calcular-precio/', expect.objectContaining({ duracion_horas: expect.any(Number) }))
    expect(wrapper.text()).toContain('S/ 120.00')
    wrapper.unmount()
  })

  it('traduce los errores de API y no presenta dinero usando float', async () => {
    api.get.mockRejectedValueOnce({ response: { status: 403, data: { detail: 'No tienes acceso a esta cancha.' } } })
    const wrapper = mount(DisponibilidadTarifada, { props: { canchaId: 88 } })
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toBe('No tienes acceso a esta cancha.')
    expect(formatearPEN('12345678901234567890.05')).toContain('12,345,678,901,234,567,890.05')
    wrapper.unmount()
  })

  it('conserva tokens de marca y los temas claro y oscuro en el panel administrativo', () => {
    const css = readFileSync(resolve(import.meta.dirname, '../src/modules/administracion/admin.css'), 'utf8')
    const tokens = readFileSync(resolve(import.meta.dirname, '../src/shared/styles/tokens.css'), 'utf8')
    expect(css).toContain('var(--brand-lime)')
    expect(tokens).toContain("data-theme='dark'")
    expect(tokens).toContain('#C0FA04')
  })
})

describe('servicio de tarifas', () => {
  it('apunta a las rutas administrativas documentadas', async () => {
    await tarifasApi.listar(21)
    await tarifasApi.crear(21, { tipo: 'diurna', precio_hora: '50.00' })
    await tarifasApi.actualizar(21, 8, { precio_hora: '70.00' })
    await tarifasApi.cambiarEstado(21, 8, false)
    expect(api.get).toHaveBeenCalledWith('/canchas/21/tarifas/')
    expect(api.post).toHaveBeenCalledWith('/canchas/21/tarifas/', { tipo: 'diurna', precio_hora: '50.00' })
    expect(api.patch).toHaveBeenCalledWith('/canchas/21/tarifas/8/', { precio_hora: '70.00' })
    expect(api.post).toHaveBeenLastCalledWith('/canchas/21/tarifas/8/estado/', { activa: false, confirmar: true })
  })
})
