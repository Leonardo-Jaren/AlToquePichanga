import api from '@/shared/services/api'

const empresa = (id) => `/empresas/administradas/${id}`

export const empresasApi = {
  listar: (params = {}) => api.get('/empresas/administradas/', { params }),
  registrar: (datos) => api.post('/empresas/', datos),
  detalle: (id) => api.get(`${empresa(id)}/`),
  actualizar: (id, datos) => api.patch(`${empresa(id)}/`, datos),
  actualizarLogo: (id, archivo) => {
    const formulario = new FormData()
    formulario.append('logotipo', archivo)
    return api.patch(`${empresa(id)}/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  listarSedes: (id) => api.get('/sedes/', { params: { empresa: id } }),
  crearSede: (datos) => api.post('/sedes/', datos),
  actualizarSede: (id, datos) => api.patch(`/sedes/${id}/`, datos, datos instanceof FormData
    ? { headers: { 'Content-Type': 'multipart/form-data' } }
    : {}),
  estadoSede: (id, activa) => api.post(`/sedes/${id}/estado/`, { activa, confirmar: true }),
  imagenSede: (id, archivo, descripcion = '') => {
    const formulario = new FormData()
    formulario.append('archivo', archivo)
    formulario.append('descripcion', descripcion)
    return api.post(`/sedes/${id}/imagenes/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  retirarImagenSede: (sede, imagen) => api.post(
    `/sedes/${sede}/imagenes/${imagen}/retirar/`, { confirmar: true },
  ),
  listarPersonal: (id) => api.get(`${empresa(id)}/personal/`),
  invitarPersonal: (id, datos) => api.post(`${empresa(id)}/personal/`, datos),
  revocarPersonal: (empresaId, membresiaId) => api.post(
    `${empresa(empresaId)}/personal/${membresiaId}/revocar/`, { confirmar: true },
  ),
  revocarInvitacion: (empresaId, invitacionId) => api.post(
    `${empresa(empresaId)}/invitaciones/${invitacionId}/revocar/`, { confirmar: true },
  ),
  planes: () => api.get('/suscripciones/planes/'),
  suscripcion: (id) => api.get(`${empresa(id)}/suscripcion/`),
  solicitarSuscripcion: (id, datos) => api.post(`${empresa(id)}/suscripcion/`, datos),
  aceptarInvitacion: (token) => api.post('/empresas/invitaciones/aceptar/', { token }),
}

export const plataformaApi = {
  empresas: (params = {}) => api.get('/empresas/plataforma/', { params }),
  detalleEmpresa: (id) => api.get(`/empresas/plataforma/${id}/`),
  estadoEmpresa: (id, estado) => api.patch(`/empresas/plataforma/${id}/`, { estado }),
  planes: () => api.get('/plataforma/planes/'),
  guardarPlan: (datos, id) => id
    ? api.patch(`/plataforma/planes/${id}/`, datos)
    : api.post('/plataforma/planes/', datos),
  solicitudes: (params = {}) => api.get('/plataforma/solicitudes/', { params }),
  resolverSolicitud: (id, datos) => api.post(`/plataforma/solicitudes/${id}/resolver/`, datos),
  estadoSuscripcion: (id, estado) => api.post(
    `/plataforma/empresas/${id}/suscripcion/estado/`, { estado },
  ),
  configuracion: () => api.get('/plataforma/suscripciones/configuracion/'),
  guardarConfiguracion: (datos) => api.put('/plataforma/suscripciones/configuracion/', datos),
}
