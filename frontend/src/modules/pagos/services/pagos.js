import api from '@/shared/services/api'

export const pagosApi = {
  obtenerReserva: (codigo) => api.get(`/pagos/reservas/${codigo}/`),
  solicitar: (codigo, datos) => api.post(`/pagos/reservas/${codigo}/solicitudes/`, datos),
  declarar: (codigo, pagoId, datos) => api.post(`/pagos/reservas/${codigo}/${pagoId}/declarar/`, datos),
  listarAdministracion: (params = {}) => api.get('/pagos/administracion/', { params }),
  detalleAdministracion: (pagoId) => api.get(`/pagos/administracion/${pagoId}/`),
  aprobar: (pagoId, datos) => api.post(`/pagos/administracion/${pagoId}/aprobar/`, datos),
  rechazar: (pagoId, datos) => api.post(`/pagos/administracion/${pagoId}/rechazar/`, datos),
  listarMedios: (sedeId) => api.get(`/pagos/sedes/${sedeId}/medios/`),
  guardarMedio: (sedeId, datos) => api.post(`/pagos/sedes/${sedeId}/medios/`, datos, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }),
}

export function generarClavePago() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`
}
