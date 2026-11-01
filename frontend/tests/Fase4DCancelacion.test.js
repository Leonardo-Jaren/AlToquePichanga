import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CancelacionReservaModal from '@/modules/reservas/components/CancelacionReservaModal.vue'
import { reservasApi } from '@/modules/reservas/services/reservas'

const stubs = { ModalBase: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /><slot name="pie" /></div>' } }
afterEach(() => vi.restoreAllMocks())

describe('Cancelación', () => {
  it('exige motivo, explica la política y conserva el resultado del servidor', async () => {
    const cancelar = vi.spyOn(reservasApi, 'cancelarReserva').mockResolvedValue({ data: { requiere_revision: true } })
    const wrapper = mount(CancelacionReservaModal, { props: { modelValue: true, codigo: 'ATP-ABC' }, global: { stubs } })
    expect(wrapper.text()).toContain('no generan devolución')
    await wrapper.findAll('button').find((b) => b.text().includes('Confirmar cancelación')).trigger('click')
    expect(wrapper.get('[role="alert"]').text()).toContain('motivo')
    await wrapper.get('textarea').setValue('Cambio de planes')
    await wrapper.findAll('button').find((b) => b.text().includes('Confirmar cancelación')).trigger('click')
    await flushPromises()
    expect(cancelar).toHaveBeenCalledWith('ATP-ABC', { motivo: 'Cambio de planes' })
    expect(wrapper.emitted('cancelada')[0][0].requiere_revision).toBe(true)
  })
})
