import { expect, it } from 'vitest'
import api from '@/shared/services/api'

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
