import { expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'
import { useEmpresasStore } from '@/modules/empresas/stores/empresas'
import { instalarManejoSesion } from '@/modules/autenticacion/services/manejoSesion'
import { EVENTO_SESION_EXPIRADA } from '@/shared/services/eventosSesion'

it('limpia la identidad y el contexto de empresa y redirige al login ante sesión expirada', () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const auth = useAutenticacionStore(pinia)
  const empresas = useEmpresasStore(pinia)
  auth.usuario = { id: 5, correo: 'dueno@example.test' }
  empresas.lista = [{ id: 12, nombre: 'Empresa privada' }]
  empresas.seleccionar(12)
  const router = { replace: vi.fn() }
  const retirar = instalarManejoSesion(router, pinia)
  window.dispatchEvent(new Event(EVENTO_SESION_EXPIRADA))
  expect(auth.usuario).toBeNull()
  expect(empresas.lista).toEqual([])
  expect(empresas.activaId).toBeNull()
  expect(localStorage.getItem('altoque.empresa-activa')).toBeNull()
  expect(router.replace).toHaveBeenCalledWith('/ingresar')
  retirar()
})
