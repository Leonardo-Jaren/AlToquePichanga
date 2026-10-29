import api from '@/shared/services/api'

export const tarifasApi = {
  listar: (canchaId) => api.get(`/canchas/${canchaId}/tarifas/`),
  crear: (canchaId, datos) => api.post(`/canchas/${canchaId}/tarifas/`, datos),
  actualizar: (canchaId, tarifaId, datos) => api.patch(`/canchas/${canchaId}/tarifas/${tarifaId}/`, datos),
  cambiarEstado: (canchaId, tarifaId, activa) => api.post(
    `/canchas/${canchaId}/tarifas/${tarifaId}/estado/`, { activa, confirmar: true },
  ),
  calcular: (canchaId, datos) => api.post(`/canchas/${canchaId}/calcular-precio/`, datos),
  cotizarPublico: (canchaId, datos) => api.post(`/publico/canchas/${canchaId}/cotizar/`, datos),
}
