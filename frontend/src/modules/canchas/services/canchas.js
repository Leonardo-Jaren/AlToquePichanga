import api from '@/shared/services/api'

const rutaCanchas = '/canchas/'

export const canchasApi = {
  listar: (params = {}) => api.get(rutaCanchas, { params }),
  detalle: (id) => api.get(`${rutaCanchas}${id}/`),
  crear: (datos) => api.post(rutaCanchas, datos),
  actualizar: (id, datos) => api.patch(`${rutaCanchas}${id}/`, datos),
  actualizarImagenPrincipal: (id, archivo) => {
    const formulario = new FormData()
    formulario.append('imagen_principal', archivo)
    return api.patch(`${rutaCanchas}${id}/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  cambiarEstado: (id, estado) => api.post(`${rutaCanchas}${id}/estado/`, {
    estado,
    confirmar: true,
  }),
  subirImagen: (id, { archivo, descripcion = '', orden }) => {
    const formulario = new FormData()
    formulario.append('archivo', archivo)
    if (descripcion.trim()) formulario.append('descripcion', descripcion.trim())
    if (orden !== undefined && orden !== null) formulario.append('orden', String(orden))
    return api.post(`${rutaCanchas}${id}/imagenes/`, formulario, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  retirarImagen: (canchaId, imagenId) => api.post(
    `${rutaCanchas}${canchaId}/imagenes/${imagenId}/retirar/`, { confirmar: true },
  ),
  listarSedes: () => api.get('/sedes/'),
  listarPublicas: () => api.get('/publico/canchas/'),
}

export function datosCanchaParaFormulario(cancha = {}) {
  const sede = cancha.sede_id ?? (typeof cancha.sede === 'object'
    ? cancha.sede?.id
    : (typeof cancha.sede === 'number' ? cancha.sede : ''))
  const caracteristicas = Array.isArray(cancha.caracteristicas)
    ? cancha.caracteristicas.join('\n')
    : (cancha.caracteristicas || '')
  return {
    sede_id: sede || '',
    nombre: cancha.nombre || '',
    descripcion: cancha.descripcion || '',
    modalidad: cancha.modalidad ?? '',
    tipo_superficie: cancha.tipo_superficie || '',
    capacidad_jugadores: cancha.capacidad_jugadores ?? '',
    techada: Boolean(cancha.techada),
    iluminacion: Boolean(cancha.iluminacion),
    publicada: Boolean(cancha.publicada),
    caracteristicas,
  }
}
