import api from '@/shared/services/api'

export const reservasApi = {
  solicitar: (datos) => api.post('/reservas/', datos),
  listarPropias: (params = {}) => api.get('/reservas/mias/', { params }),
  obtenerPropia: (codigo) => api.get(`/reservas/${codigo}/`),
  cancelar: (codigo) => api.post(`/reservas/${codigo}/cancelar/`, {}),
  listarAdministracion: (params = {}) => api.get('/reservas/administracion/', { params }),
  obtenerAdministracion: (codigo) => api.get(`/reservas/administracion/${codigo}/`),
  disponibilidadAdministracion: (canchaId, desde, hasta) => api.get(
    `/reservas/administracion/disponibilidad/${canchaId}/`, { params: { desde, hasta } },
  ),
}

export function generarClaveIdempotencia() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  const bytes = new Uint8Array(16)
  globalThis.crypto.getRandomValues(bytes)
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hexadecimal = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hexadecimal.slice(0, 8)}-${hexadecimal.slice(8, 12)}-${hexadecimal.slice(12, 16)}-${hexadecimal.slice(16, 20)}-${hexadecimal.slice(20)}`
}
