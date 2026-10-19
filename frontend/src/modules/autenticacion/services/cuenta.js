import api from '@/shared/services/api'

export const cuenta = {
  perfil: () => api.get('/auth/perfil/'),
  ingresar: (datos) => api.post('/auth/login/', datos),
  registrar: (datos) => api.post('/auth/registro/', datos),
  salir: () => api.post('/auth/logout/'),
  actualizar: (datos) => api.patch('/auth/perfil/', datos),
  recuperar: (datos) => api.post('/auth/recuperar/', datos),
  restablecer: (datos) => api.post('/auth/restablecer/', datos),
  verificar: (datos) => api.post('/auth/verificar-correo/', datos),
  google: (vincular = false) => api.post('/auth/google/iniciar/', { vincular }),
  panel: (rol) => api.get(`/panel/${rol}/`),
}
