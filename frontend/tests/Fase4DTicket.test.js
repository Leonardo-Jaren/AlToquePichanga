import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import TicketReservaModal from '@/modules/reservas/components/TicketReservaModal.vue'
import { reservasApi } from '@/modules/reservas/services/reservas'

const stubs = { ModalBase: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /><slot name="pie" /></div>' } }
const ticket = {
  codigo: 'ATP-ABC', sede: 'Sede A', cancha: 'Cancha A', jugador: 'Jugador', estado: 'confirmada',
  inicio: '2026-11-10T18:00:00-05:00', fin: '2026-11-10T19:00:00-05:00',
  importe_total: '50.00', importe_pagado: '25.00', saldo_pendiente: '25.00', moneda: 'PEN',
}

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('Ticket de reserva', () => {
  it('muestra el saldo y permite descargar el QR privado', async () => {
    vi.spyOn(reservasApi, 'ticket').mockResolvedValue({ data: ticket })
    vi.spyOn(reservasApi, 'ticketQr').mockResolvedValue({ data: new Blob(['svg']) })
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:ticket'), revokeObjectURL: vi.fn() })
    const wrapper = mount(TicketReservaModal, { props: { modelValue: true, codigo: ticket.codigo }, global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('Cancha A')
    expect(wrapper.text()).toContain('Saldo pendiente')
    expect(wrapper.get('img[alt="Código QR de la reserva confirmada"]').attributes('src')).toBe('blob:ticket')
    expect(wrapper.get('a[download]').attributes('download')).toBe('qr-ATP-ABC.svg')
    wrapper.unmount()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:ticket')
  })

  it('muestra un error si no puede consultar el ticket', async () => {
    vi.spyOn(reservasApi, 'ticket').mockRejectedValue(new Error('sin acceso'))
    vi.spyOn(reservasApi, 'ticketQr').mockResolvedValue({ data: new Blob() })
    const wrapper = mount(TicketReservaModal, { props: { modelValue: true, codigo: ticket.codigo }, global: { stubs } })
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('No se pudo cargar el ticket')
  })
})
