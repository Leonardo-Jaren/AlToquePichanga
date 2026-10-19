import { beforeEach, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { createPinia } from 'pinia'
import { instalarProteccion } from '@/router/proteccion'
import { cuenta } from '@/modules/autenticacion/services/cuenta'

vi.mock('@/modules/autenticacion/services/cuenta', () => ({ cuenta: { perfil: vi.fn() } }))
const jugador = { es_jugador: true, es_superadministrador: false, membresias: [] }
let router
beforeEach(() => {
  vi.clearAllMocks()
  const componente = { template: '<div />' }
  router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/', component: componente },
    { path: '/ingresar', name: 'ingresar', component: componente, meta: { invitado: true } },
    { path: '/perfil', component: componente, meta: { autenticado: true } },
    { path: '/sin-permiso', name: 'sin-permiso', component: componente },
    { path: '/sesion-no-disponible', name: 'sesion-no-disponible', component: componente },
    ...['jugador', 'dueno', 'administrador_sede', 'cajero', 'plataforma'].map((rol) => ({
      path: `/panel/${rol}`, component: componente, meta: { autenticado: true, rol },
    })),
  ] })
  instalarProteccion(router, createPinia())
})

it('redirige al visitante que intenta abrir una ruta privada', async () => {
  cuenta.perfil.mockRejectedValue({ response: { status: 401 } })
  await router.push('/perfil')
  expect(router.currentRoute.value.name).toBe('ingresar')
})
it.each(['dueno', 'administrador_sede', 'cajero', 'plataforma'])('deniega %s a un jugador', async (rol) => {
  cuenta.perfil.mockResolvedValue({ data: jugador })
  await router.push(`/panel/${rol}`)
  expect(router.currentRoute.value.name).toBe('sin-permiso')
})
it.each(['dueno', 'administrador_sede', 'cajero'])('autoriza y redirige al rol %s', async (rol) => {
  cuenta.perfil.mockResolvedValue({ data: { ...jugador, membresias: [{ rol, empresa_id: 1 }] } })
  await router.push('/ingresar')
  expect(router.currentRoute.value.path).toBe(`/panel/${rol}`)
})
it('autoriza al superadministrador de plataforma', async () => {
  cuenta.perfil.mockResolvedValue({ data: { ...jugador, es_superadministrador: true } })
  await router.push('/ingresar')
  expect(router.currentRoute.value.path).toBe('/panel/plataforma')
})
it('un fallo de red impide abrir el panel y ofrece reintentar', async () => {
  cuenta.perfil.mockRejectedValue(new Error('Sin red'))
  await router.push('/perfil')
  expect(router.currentRoute.value.name).toBe('sesion-no-disponible')
})
