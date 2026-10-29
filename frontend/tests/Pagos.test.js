import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createMemoryHistory, createRouter } from 'vue-router'
import PagoReservaView from '@/modules/pagos/views/PagoReservaView.vue'
import PagosAdminPanel from '@/modules/pagos/components/PagosAdminPanel.vue'
import api from '@/shared/services/api'
import { pagosApi } from '@/modules/pagos/services/pagos'
import { etiquetaEstadoPago, soles } from '@/modules/pagos/utils/pagos'

vi.mock('@/shared/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

const codigo = 'ATP-AB12CD34EF56'
const metodo = {
  id: 7, tipo: 'yape', etiqueta: 'Yape', titular: 'Titular ficticio',
  numero_cuenta: '00000000000', banco: '', cci: '', instrucciones: '', imagen_qr_url: null, activo: true,
}
const base = {
  codigo, cancha: 'Cancha Centro', sede: 'Sede Centro',
  inicio: '2026-10-26T18:00:00-05:00', fin: '2026-10-26T19:00:00-05:00',
  estado_reserva: 'retenida', moneda: 'PEN', importe_total: '50.00',
  adelanto_minimo: '25.00', importe_pagado: '0.00', saldo_pendiente: '50.00',
  vence_en: '2026-10-25T20:15:00Z', whatsapp_url: 'https://wa.me/00000000000?text=ATP',
  habilitado: true, metodos: [metodo], pagos: [],
}
const pagoPendiente = {
  id: 91, codigo_reserva: codigo, estado: 'pendiente_pago', tipo: 'total',
  importe_solicitado: '50.00', importe_verificado: '0.00', referencia: '',
  observacion_jugador: '', motivo_revision: '', creado_en: '2026-10-25T20:00:00Z',
  declarado_en: null, revisado_en: null, requiere_conciliacion: false,
  metodo, historial: [],
}
const pagoRevision = { ...pagoPendiente, estado: 'pendiente_revision', referencia: 'E2E-REF' }
const pagoRechazado = { ...pagoPendiente, estado: 'rechazado', motivo_revision: 'No aparece en la cuenta de la sede.' }
const pagoAdmin = {
  ...pagoRevision, empresa: 'Empresa A', sede: 'Sede A', cancha: 'Cancha A',
  jugador: { nombre: 'Jugador Demo', correo: 'demo@example.test' },
  historial: [{ estado_anterior: 'pendiente_pago', estado_nuevo: 'pendiente_revision',
    motivo: 'Comprobante declarado.', actor: 'Jugador Demo', creado_en: '2026-10-25T20:01:00Z' }],
}

const stubs = {
  ThemeSelector: { template: '<span aria-label="Selector de tema" />' },
  ModalBase: {
    props: ['modelValue', 'titulo'],
    emits: ['update:modelValue'],
    template: '<div v-if="modelValue" role="dialog"><h2>{{ titulo }}</h2><slot /><footer><slot name="pie" /></footer></div>',
  },
}

async function montarPago() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/mis-reservas', component: { template: '<span>Mis reservas</span>' } },
      { path: '/mis-reservas/:codigo/pago', component: PagoReservaView },
    ],
  })
  await router.push(`/mis-reservas/${codigo}/pago`)
  await router.isReady()
  const wrapper = mount(PagoReservaView, { global: { plugins: [router], stubs } })
  await flushPromises()
  return wrapper
}

beforeEach(() => vi.resetAllMocks())
afterEach(() => vi.restoreAllMocks())

describe('flujo de pago del jugador', () => {
  it('calcula el importe en servidor, muestra WhatsApp sin abrirlo y declara para revisión manual', async () => {
    vi.spyOn(pagosApi, 'obtenerReserva')
      .mockResolvedValueOnce({ data: base })
      .mockResolvedValueOnce({ data: { ...base, pagos: [pagoPendiente] } })
      .mockResolvedValueOnce({ data: { ...base, pagos: [pagoRevision] } })
    vi.spyOn(pagosApi, 'solicitar').mockResolvedValue({ data: pagoPendiente })
    vi.spyOn(pagosApi, 'declarar').mockResolvedValue({ data: pagoRevision })
    const wrapper = await montarPago()

    expect(wrapper.text()).toContain('Adelanto mínimo · 50%')
    await wrapper.get('input[type="radio"][value="total"]').setValue()
    await wrapper.findAll('button').find((boton) => boton.text().includes('Continuar')).trigger('click')
    await flushPromises()

    expect(pagosApi.solicitar).toHaveBeenCalledWith(codigo, expect.objectContaining({
      tipo: 'total', metodo_id: metodo.id, clave_idempotencia: expect.any(String),
    }))
    const whatsapp = wrapper.get('a.enlace-whatsapp')
    expect(whatsapp.attributes('href')).toContain('https://wa.me/00000000000?text=')
    expect(whatsapp.attributes('target')).toBe('_blank')
    expect(pagosApi.declarar).not.toHaveBeenCalled()

    await wrapper.get('input.pago-input').setValue('E2E-REF')
    await wrapper.get('form.declaracion-form').trigger('submit')
    await flushPromises()

    expect(pagosApi.declarar).toHaveBeenCalledWith(codigo, pagoPendiente.id, {
      referencia: 'E2E-REF', observacion: '',
    })
    expect(wrapper.text()).toContain('La sede revisará tu comprobante')
    expect(wrapper.text()).toContain('no aprueban el pago automáticamente')
    expect(wrapper.text()).not.toContain('Aprobar pago')
    wrapper.unmount()
  })

  it('mantiene el flujo pausado cuando la configuración de pagos está deshabilitada', async () => {
    vi.spyOn(pagosApi, 'obtenerReserva').mockResolvedValue({ data: { ...base, habilitado: false } })
    const wrapper = await montarPago()

    expect(wrapper.text()).toContain('Los pagos manuales se habilitarán')
    expect(wrapper.text()).not.toContain('Continuar')
    wrapper.unmount()
  })

  it('muestra el motivo de rechazo y permite iniciar una nueva solicitud mientras la reserva siga vigente', async () => {
    vi.spyOn(pagosApi, 'obtenerReserva').mockResolvedValue({
      data: { ...base, estado_reserva: 'pendiente_pago', pagos: [pagoRechazado] },
    })
    const wrapper = await montarPago()

    expect(wrapper.get('[role="status"]').text()).toContain('No aparece en la cuenta de la sede.')
    expect(wrapper.text()).toContain('Puedes enviar una nueva solicitud mientras siga vigente')
    expect(wrapper.findAll('button').some((boton) => boton.text().includes('Continuar'))).toBe(true)
    wrapper.unmount()
  })
})

describe('cola administrativa de pagos', () => {
  it('filtra la cola autorizada, permite revisar el monto y mantiene fuera la edición para cajeros', async () => {
    vi.spyOn(pagosApi, 'listarAdministracion').mockResolvedValue({ data: { count: 1, results: [pagoAdmin] } })
    vi.spyOn(pagosApi, 'listarMedios').mockResolvedValue({ data: [metodo] })
    vi.spyOn(pagosApi, 'detalleAdministracion').mockResolvedValue({ data: pagoAdmin })
    vi.spyOn(pagosApi, 'aprobar').mockResolvedValue({ data: { ...pagoAdmin, estado: 'aprobado' } })
    vi.spyOn(pagosApi, 'rechazar').mockResolvedValue({ data: { ...pagoAdmin, estado: 'rechazado' } })
    api.get.mockResolvedValue({ data: [] })
    const wrapper = mount(PagosAdminPanel, {
      props: { sedes: [{ id: 3, nombre: 'Sede A' }] },
      global: { stubs },
    })
    await flushPromises()

    expect(pagosApi.listarAdministracion).toHaveBeenCalledWith(expect.objectContaining({ estado: 'pendiente_revision' }))
    expect(wrapper.text()).toContain(codigo)
    expect(wrapper.text()).toContain('Jugador Demo')
    expect(wrapper.text()).toContain('Solo los dueños y administradores')
    expect(wrapper.text()).not.toContain('Titular de la cuenta')

    await wrapper.findAll('button').find((boton) => boton.text().includes('Revisar')).trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="dialog"]').text()).toContain('El personal debe comprobar')
    await wrapper.get('[role="dialog"] input[type="number"]').setValue('50.00')
    await wrapper.findAll('button').find((boton) => boton.text().includes('Aprobar pago')).trigger('click')
    await flushPromises()

    expect(pagosApi.aprobar).toHaveBeenCalledWith(pagoAdmin.id, {
      importe_verificado: 50, motivo: '',
    })
    expect(wrapper.text()).toContain('La reserva queda pendiente de confirmación')
    wrapper.unmount()
  })

  it('edita un medio de pago en un modal con controles de guardar y cancelar', async () => {
    vi.spyOn(pagosApi, 'listarAdministracion').mockResolvedValue({ data: { count: 0, results: [] } })
    vi.spyOn(pagosApi, 'listarMedios').mockResolvedValue({ data: [metodo] })
    vi.spyOn(pagosApi, 'guardarMedio').mockResolvedValue({ data: metodo })
    api.get.mockResolvedValue({ data: [] })
    const wrapper = mount(PagosAdminPanel, {
      props: { sedes: [{ id: 3, nombre: 'Sede A' }], configurarMedios: true },
      global: { stubs },
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Visible')
    expect(wrapper.find('input[required]').exists()).toBe(false)
    await wrapper.findAll('button').find((boton) => boton.text().includes('Editar Yape')).trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="dialog"]').text()).toContain('Titular de la cuenta')
    expect(wrapper.get('[role="dialog"]').text()).toContain('Cancelar')

    await wrapper.get('form.metodo-form').trigger('submit')
    await flushPromises()
    expect(pagosApi.guardarMedio).toHaveBeenCalledWith(3, expect.any(FormData))
    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('usa las etiquetas y formato monetario PEN de los estados de pago', () => {
    expect(etiquetaEstadoPago('pendiente_revision')).toBe('Comprobante por revisar')
    expect(etiquetaEstadoPago('pago_tardio')).toBe('Declarado fuera de plazo')
    expect(soles('25.50')).toContain('25.50')
  })
})
