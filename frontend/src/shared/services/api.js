import axios from 'axios'
import { EVENTO_SESION_EXPIRADA } from './eventosSesion'

/**
 * Cliente HTTP unificado para la API de AlToque Pichanga.
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 10000,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

api.interceptors.response.use((respuesta) => respuesta, (error) => {
  const url = String(error.config?.url || '')
  if (error.response?.status === 401 && !url.includes('/auth/') && typeof window !== 'undefined') {
    window.dispatchEvent(new Event(EVENTO_SESION_EXPIRADA))
  }
  return Promise.reject(error)
})

// El token CSRF se obtiene en memoria, también después de que Django lo rote al ingresar.
api.interceptors.request.use(async (config) => {
  if (!['get', 'head', 'options'].includes((config.method || 'get').toLowerCase())) {
    const { data } = await api.get('/auth/csrf/')
    config.headers['X-CSRFToken'] = data.csrfToken
  }
  return config
})

export default api
