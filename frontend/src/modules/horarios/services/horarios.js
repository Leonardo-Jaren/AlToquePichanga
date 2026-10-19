import api from '@/shared/services/api'

export const horariosApi = {
  horarioSede: (sedeId) => api.get(`/sedes/${sedeId}/horario-semanal/`),
  guardarHorarioSede: (sedeId, datos) => api.put(`/sedes/${sedeId}/horario-semanal/`, datos),
  horarioCancha: (canchaId) => api.get(`/canchas/${canchaId}/horario-semanal/`),
  guardarHorarioCancha: (canchaId, datos) => api.put(`/canchas/${canchaId}/horario-semanal/`, datos),
  listarCanchas: (sedeId) => api.get('/canchas/', { params: { sede: sedeId, page_size: 100 } }),
  listarExcepciones: (params) => api.get('/horarios/excepciones/', { params }),
  crearExcepcion: (datos) => api.post('/horarios/excepciones/', datos),
  anularExcepcion: (id) => api.post(`/horarios/excepciones/${id}/anular/`, { confirmar: true }),
  disponibilidad: (canchaId, desde, hasta) => api.get(
    `/canchas/${canchaId}/disponibilidad-operativa/`, { params: { desde, hasta } },
  ),
}
