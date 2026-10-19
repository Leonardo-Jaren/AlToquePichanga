import { beforeEach, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'
import GoogleRetornoView from '@/modules/autenticacion/views/GoogleRetornoView.vue'
import { cuenta } from '@/modules/autenticacion/services/cuenta'

const { ruta, replace } = vi.hoisted(() => ({ ruta: { query: {} }, replace: vi.fn() }))
vi.mock('vue-router', () => ({ useRoute: () => ruta, useRouter: () => ({ replace }) }))
vi.mock('@/modules/autenticacion/services/cuenta', () => ({ cuenta: { perfil: vi.fn() } }))
const montar = () => mount(GoogleRetornoView, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks(); ruta.query = {} })

it('recupera la sesión del callback sin recibir tokens en Vue', async () => {
  cuenta.perfil.mockResolvedValue({ data: { es_jugador: true, membresias: [] } })
  montar(); await flushPromises()
  expect(replace).toHaveBeenCalledWith('/panel/jugador')
})
it('muestra cancelación o fallo sin dar por iniciada una sesión', async () => {
  ruta.query = { error: 'autorizacion' }
  const w = montar(); await flushPromises()
  expect(w.text()).toContain('No se pudo completar el acceso con Google')
  expect(cuenta.perfil).not.toHaveBeenCalled()
})
it('explica el fallo de red y permite volver al inicio de sesión', async () => {
  cuenta.perfil.mockRejectedValue(new Error('Sin conexión'))
  const w = montar(); await flushPromises()
  expect(w.text()).toContain('Comprueba tu conexión')
})
