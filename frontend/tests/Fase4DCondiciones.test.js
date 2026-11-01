import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CondicionesSedePanel from '@/modules/pagos/components/CondicionesSedePanel.vue'
import { pagosApi } from '@/modules/pagos/services/pagos'

afterEach(() => vi.restoreAllMocks())

describe('Condiciones de la sede', () => {
  it('muestra la versión vigente y permite publicar una versión nueva', async () => {
    vi.spyOn(pagosApi, 'obtenerCondiciones').mockResolvedValue({ data: { version: 1, texto: 'Condiciones vigentes' } })
    vi.spyOn(pagosApi, 'guardarCondiciones').mockResolvedValue({ data: { version: 2, texto: 'Nuevas condiciones' } })
    const wrapper = mount(CondicionesSedePanel, { props: { sedeId: 7 } })
    await flushPromises()
    expect(wrapper.text()).toContain('Versión vigente: 1')
    await wrapper.get('textarea').setValue('Nuevas condiciones')
    await wrapper.findAll('button').find((b) => b.text().includes('Guardar condiciones')).trigger('click')
    await flushPromises()
    expect(pagosApi.guardarCondiciones).toHaveBeenCalledWith(7, { texto: 'Nuevas condiciones' })
    expect(wrapper.text()).toContain('versión 2')
  })

  it('descarta la respuesta tardía de otra sede', async () => {
    let resolverPrimera
    vi.spyOn(pagosApi, 'obtenerCondiciones')
      .mockImplementationOnce(() => new Promise((resolve) => { resolverPrimera = resolve }))
      .mockResolvedValueOnce({ data: { version: 2, texto: 'Condiciones sede B' } })
    const wrapper = mount(CondicionesSedePanel, { props: { sedeId: 7 } })
    await wrapper.setProps({ sedeId: 8 })
    await flushPromises()
    resolverPrimera({ data: { version: 1, texto: 'Condiciones sede A' } })
    await flushPromises()
    expect(wrapper.get('textarea').element.value).toBe('Condiciones sede B')
  })

})
