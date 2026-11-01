import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ValidarIngreso from '@/modules/reservas/components/ValidarIngreso.vue'
import { reservasApi } from '@/modules/reservas/services/reservas'

const resultado = { codigo: 'ATP-ABC', sede: 'Sede A', cancha: 'Cancha A', inicio: '2026-11-10T18:00:00-05:00', fin: '2026-11-10T19:00:00-05:00', saldo_pendiente: '25.00', moneda: 'PEN', asistencia_registrada: false }
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })

describe('Validación de ingreso', () => {
  it('consulta el código y registra una asistencia', async () => {
    vi.spyOn(reservasApi, 'consultarIngreso').mockResolvedValue({ data: resultado })
    vi.spyOn(reservasApi, 'registrarIngreso').mockResolvedValue({ data: {} })
    const wrapper = mount(ValidarIngreso)
    await wrapper.get('input').setValue('ATP-ABC')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('Saldo pendiente')
    await wrapper.findAll('button').find((b) => b.text().includes('Registrar ingreso')).trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('Ingreso ya registrado')
    expect(reservasApi.registrarIngreso).toHaveBeenCalledWith({ tipo: 'codigo', valor: 'ATP-ABC' })
  })

  it('ofrece ingreso manual si no hay cámara compatible', async () => {
    vi.stubGlobal('BarcodeDetector', undefined)
    const wrapper = mount(ValidarIngreso)
    await wrapper.findAll('button').find((b) => b.text().includes('Abrir cámara')).trigger('click')
    expect(wrapper.text()).toContain('Ingresa el código de reserva')
  })

  it('informa cuando el QR o código no se puede validar', async () => {
    vi.spyOn(reservasApi, 'consultarIngreso').mockRejectedValue(new Error('inválido'))
    const wrapper = mount(ValidarIngreso)
    await wrapper.get('input').setValue('ATP-INVALIDO')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('No se pudo validar la reserva')
  })
})
