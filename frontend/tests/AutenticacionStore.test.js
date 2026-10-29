import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { cuenta } from '@/modules/autenticacion/services/cuenta'
import { destinoUsuario, puedeAcceder, useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'
import { useEmpresasStore } from '@/modules/empresas/stores/empresas'

vi.mock('@/modules/autenticacion/services/cuenta', () => ({
  cuenta: { perfil: vi.fn(), ingresar: vi.fn(), registrar: vi.fn(), salir: vi.fn(), actualizar: vi.fn() },
}))
export const jugador = { id: 1, correo: 'uno@example.com', nombre: 'Uno', es_jugador: true,
  es_superadministrador: false, membresias: [] }
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks(); localStorage.clear() })

describe('Sesión de servidor', () => {
  it('restaura la sesión al recargar sin guardar credenciales en localStorage', async () => {
    cuenta.perfil.mockResolvedValue({ data: jugador })
    const auth = useAutenticacionStore()
    await auth.recuperarSesion()
    expect(auth.autenticado).toBe(true)
    expect(localStorage.length).toBe(0)
    setActivePinia(createPinia())
    await useAutenticacionStore().recuperarSesion()
    expect(cuenta.perfil).toHaveBeenCalledTimes(2)
  })
  it('comparte la petición simultánea y elimina sesión vencida', async () => {
    cuenta.perfil.mockResolvedValue({ data: jugador })
    const auth = useAutenticacionStore()
    await Promise.all([auth.recuperarSesion(), auth.recuperarSesion()])
    expect(cuenta.perfil).toHaveBeenCalledTimes(1)
    cuenta.perfil.mockRejectedValue({ response: { status: 401 } })
    const empresas = useEmpresasStore()
    empresas.lista = [{ id: 8, nombre: 'Empresa anterior' }]
    empresas.seleccionar(8)
    expect(await auth.recuperarSesion()).toBeNull()
    expect(auth.autenticado).toBe(false)
    expect(empresas.lista).toEqual([])
    expect(empresas.activaId).toBeNull()
    expect(localStorage.getItem('altoque.empresa-activa')).toBeNull()
  })
  it('propaga fallo de red sin afirmar que la sesión se cerró', async () => {
    cuenta.ingresar.mockResolvedValue({ data: jugador })
    const auth = useAutenticacionStore()
    await auth.ingresar({})
    cuenta.salir.mockRejectedValue(new Error('Sin red'))
    await expect(auth.salir()).rejects.toThrow('Sin red')
    expect(auth.autenticado).toBe(true)
  })
  it('registra, actualiza y cierra sesión mediante el backend', async () => {
    cuenta.registrar.mockResolvedValue({ data: jugador })
    cuenta.actualizar.mockResolvedValue({ data: { ...jugador, nombre: 'Nuevo' } })
    cuenta.salir.mockResolvedValue({ status: 204 })
    const auth = useAutenticacionStore()
    await auth.registrar({})
    await auth.actualizar({ nombre: 'Nuevo' })
    expect(auth.usuario.nombre).toBe('Nuevo')
    await auth.salir()
    expect(auth.usuario).toBeNull()
    expect(useEmpresasStore().lista).toEqual([])
    expect(localStorage.getItem('altoque.empresa-activa')).toBeNull()
  })
  it('reemplaza el usuario activo cuando se inicia sesión con otra cuenta', async () => {
    const otro = { ...jugador, id: 2, correo: 'dos@example.com', nombre: 'Dos' }
    cuenta.ingresar.mockResolvedValueOnce({ data: jugador }).mockResolvedValueOnce({ data: otro })
    const auth = useAutenticacionStore()
    const empresas = useEmpresasStore()
    await auth.ingresar({ correo: jugador.correo })
    empresas.lista = [{ id: 7, nombre: 'Empresa del primer usuario' }]
    empresas.seleccionar(7)
    await auth.ingresar({ correo: otro.correo })
    expect(auth.usuario).toEqual(otro)
    expect(auth.autenticado).toBe(true)
    expect(empresas.lista).toEqual([])
    expect(localStorage.getItem('altoque.empresa-activa')).toBeNull()
  })
  it.each(['dueno', 'administrador_sede', 'cajero'])('resuelve el rol %s sin perder el rol jugador', (rol) => {
    const usuario = { ...jugador, membresias: [{ empresa_id: 1, rol }] }
    expect(destinoUsuario(usuario)).toBe(`/panel/${rol}`)
    expect(puedeAcceder(usuario, 'jugador')).toBe(true)
    expect(puedeAcceder(usuario, 'plataforma')).toBe(false)
  })
  it('prioriza plataforma y rechaza permisos inexistentes', () => {
    expect(destinoUsuario({ ...jugador, es_superadministrador: true })).toBe('/panel/plataforma')
    expect(puedeAcceder(jugador, 'dueno')).toBe(false)
    expect(puedeAcceder(null, 'jugador')).toBe(false)
  })
})
