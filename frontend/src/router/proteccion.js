import { destinoUsuario, puedeAcceder, useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'

export function instalarProteccion(router, pinia) {
  router.beforeEach(async (to) => {
    if (!to.meta.autenticado && !to.meta.invitado) return true
    const auth = useAutenticacionStore(pinia)
    try { await auth.recuperarSesion() } catch { return { name: 'sesion-no-disponible' } }
    if (to.meta.autenticado && !auth.autenticado) return { name: 'ingresar' }
    if (to.meta.rol && !puedeAcceder(auth.usuario, to.meta.rol)) return { name: 'sin-permiso' }
    if (to.meta.invitado && auth.autenticado) return destinoUsuario(auth.usuario)
    return true
  })
}
