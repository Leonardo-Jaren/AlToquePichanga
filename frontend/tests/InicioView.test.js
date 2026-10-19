import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import InicioView from '@/modules/inicio/views/InicioView.vue'
import api from '@/shared/services/api'

vi.mock('@/shared/services/api', () => ({
  default: {
    get: vi.fn(),
  },
}))

describe('InicioView Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renderiza la marca y el lema principal de AlToque Pichanga', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        estado: 'operativo',
        servicio: 'AlToque Pichanga API',
        version: '0.1.0',
        fase: 'Fase 0 - Inicialización',
        base_de_datos: 'conectada',
        timestamp: '2026-10-19T00:20:00Z',
      },
    })

    const wrapper = mount(InicioView)
    await flushPromises()

    expect(wrapper.text()).toContain('AlToque')
    expect(wrapper.text()).toContain('Pichanga')
    expect(wrapper.text()).toContain('Tu pichanga, al toque.')
  })

  it('muestra la información de salud del backend al resolver la petición con éxito', async () => {
    api.get.mockResolvedValueOnce({
      data: {
        estado: 'operativo',
        servicio: 'AlToque Pichanga API',
        version: '0.1.0',
        fase: 'Fase 0 - Inicialización',
        base_de_datos: 'conectada',
        timestamp: '2026-10-19T00:20:00Z',
      },
    })

    const wrapper = mount(InicioView)
    await flushPromises()

    expect(wrapper.text()).toContain('operativo')
    expect(wrapper.text()).toContain('PostgreSQL 17 Nativo')
    expect(wrapper.text()).toContain('conectada')
    expect(wrapper.text()).toContain('AlToque Pichanga API')
  })
})
