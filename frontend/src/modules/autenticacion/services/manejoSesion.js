import { useAutenticacionStore } from '../stores/autenticacion'
import { EVENTO_SESION_EXPIRADA } from '@/shared/services/eventosSesion'

export function instalarManejoSesion(router, pinia) {
  function sesionExpirada() {
    const auth = useAutenticacionStore(pinia)
    if (!auth.autenticado) return
    auth.limpiarSesion()
    void router.replace('/ingresar')
  }

  window.addEventListener(EVENTO_SESION_EXPIRADA, sesionExpirada)
  return () => window.removeEventListener(EVENTO_SESION_EXPIRADA, sesionExpirada)
}
