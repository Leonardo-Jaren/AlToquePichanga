import { expect, it, vi } from 'vitest'
import api from '@/shared/services/api'
import { EVENTO_SESION_EXPIRADA } from '@/shared/services/eventosSesion'

it('envía cookies y un token CSRF nuevo para cada mutación', async () => {
  const original = api.defaults.adapter
  const solicitudes = []
  let token = 0
  api.defaults.adapter = async (config) => {
    solicitudes.push(config)
    return { status: 200, data: config.url === '/auth/csrf/' ? { csrfToken: `csrf-${++token}` } : {}, config, headers: {} }
  }
  try {
    await api.post('/auth/login/', {})
    await api.patch('/auth/perfil/', {})
    expect(solicitudes.map((s) => s.url)).toEqual(['/auth/csrf/', '/auth/login/', '/auth/csrf/', '/auth/perfil/'])
    expect(solicitudes[1].headers['X-CSRFToken']).toBe('csrf-1')
    expect(solicitudes[3].headers['X-CSRFToken']).toBe('csrf-2')
    expect(solicitudes.every((s) => s.withCredentials)).toBe(true)
  } finally { api.defaults.adapter = original }
})

it('expira sesiones con 401 de negocio y conserva 403 y fallos de login', async () => {
  const original = api.defaults.adapter
  const vencida = vi.fn()
  window.addEventListener(EVENTO_SESION_EXPIRADA, vencida)
  api.defaults.adapter = async (config) => {
    if (config.url === '/auth/csrf/') {
      return { status: 200, data: { csrfToken: 'csrf' }, config, headers: {} }
    }
    const status = config.url === '/canchas/denegada/' ? 403 : 401
    return Promise.reject({ config, response: { status, data: { detail: 'Respuesta de prueba.' }, config } })
  }
  try {
    await expect(api.get('/empresas/')).rejects.toMatchObject({ response: { status: 401 } })
    expect(vencida).toHaveBeenCalledTimes(1)
    await expect(api.get('/canchas/denegada/')).rejects.toMatchObject({ response: { status: 403 } })
    await expect(api.post('/auth/login/', {})).rejects.toMatchObject({ response: { status: 401 } })
    expect(vencida).toHaveBeenCalledTimes(1)
  } finally {
    window.removeEventListener(EVENTO_SESION_EXPIRADA, vencida)
    api.defaults.adapter = original
  }
})
