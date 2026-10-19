import { beforeEach, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import IngresarView from '@/modules/autenticacion/views/IngresarView.vue'
import RegistroView from '@/modules/autenticacion/views/RegistroView.vue'
import RecuperarView from '@/modules/autenticacion/views/RecuperarView.vue'
import PerfilView from '@/modules/autenticacion/views/PerfilView.vue'
import EnlaceView from '@/modules/autenticacion/views/EnlaceView.vue'
import { cuenta } from '@/modules/autenticacion/services/cuenta'
import { useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'
import { useThemeStore } from '@/stores/theme'

const { replace, ruta } = vi.hoisted(() => ({ replace: vi.fn(), ruta: { name: '', hash: '#uid=MQ&token=prueba' } }))
vi.mock('vue-router', () => ({ useRouter: () => ({ replace }), useRoute: () => ruta }))
vi.mock('@/modules/autenticacion/services/cuenta', () => ({ cuenta: {
  ingresar: vi.fn(), registrar: vi.fn(), recuperar: vi.fn(), actualizar: vi.fn(),
  google: vi.fn(), salir: vi.fn(), restablecer: vi.fn(), verificar: vi.fn(),
} }))
const usuario = { nombre: 'Ana', apellidos: '', correo: 'ana@example.com', es_jugador: true,
  es_superadministrador: false, membresias: [] }
const montar = (componente) => mount(componente, { global: { stubs: { RouterLink: { template: '<a><slot /></a>' } } } })
beforeEach(() => { setActivePinia(createPinia()); vi.clearAllMocks(); localStorage.clear() })

it.each([IngresarView, RegistroView, RecuperarView])('renderiza formularios con etiquetas y campos accesibles', (vista) => {
  const w = montar(vista)
  expect(w.get('label[for="correo"]').text()).toBe('Correo electrónico')
  expect(w.get('#correo').attributes('autocomplete')).toBe('email')
})
it('valida campos vacíos sin enviar la petición', async () => {
  const w = montar(IngresarView)
  await w.get('form').trigger('submit')
  expect(w.get('#correo').attributes('aria-invalid')).toBe('true')
  expect(w.text()).toContain('Completa este campo.')
  expect(cuenta.ingresar).not.toHaveBeenCalled()
})
it('muestra errores de API y permite reintentar el inicio de sesión', async () => {
  const w = montar(IngresarView)
  await w.get('#correo').setValue('ana@example.com')
  await w.get('#contrasena').setValue('incorrecta')
  cuenta.ingresar.mockRejectedValueOnce({ response: { data: { detail: 'Credenciales incorrectas' } } })
  await w.get('form').trigger('submit'); await flushPromises()
  expect(w.get('[role="alert"]').text()).toBe('Credenciales incorrectas')
  cuenta.ingresar.mockResolvedValue({ data: usuario })
  await w.get('form').trigger('submit'); await flushPromises()
  expect(replace).toHaveBeenCalledWith('/panel/jugador')
})
it('comprueba la confirmación de contraseña y no envía roles al registro', async () => {
  const w = montar(RegistroView)
  for (const [campo, valor] of Object.entries({ nombre: 'Ana', correo: 'ana@example.com', contrasena: 'Segura123!', confirmacion: 'Otra' })) await w.get(`#${campo}`).setValue(valor)
  await w.get('form').trigger('submit')
  expect(w.text()).toContain('Las contraseñas no coinciden.')
  cuenta.registrar.mockResolvedValue({ data: usuario })
  await w.get('#confirmacion').setValue('Segura123!')
  await w.get('form').trigger('submit'); await flushPromises()
  expect(cuenta.registrar).toHaveBeenCalledWith({ nombre: 'Ana', apellidos: '', correo: 'ana@example.com', contrasena: 'Segura123!' })
})
it('recuperación muestra un mensaje que no revela si existe el correo', async () => {
  cuenta.recuperar.mockResolvedValue({ data: {} })
  const w = montar(RecuperarView)
  await w.get('#correo').setValue('ana@example.com')
  await w.get('form').trigger('submit'); await flushPromises()
  expect(w.get('[role="status"]').text()).toContain('Si el correo corresponde a una cuenta')
})
it.each(['light', 'dark', 'system'])('mantiene formulario y selección de tema %s', async (tema) => {
  const w = montar(IngresarView)
  useThemeStore().setTheme(tema)
  await flushPromises()
  expect(w.get(`[data-theme-option="${tema}"]`).attributes('aria-checked')).toBe('true')
  expect(document.documentElement.dataset.theme).toBe(tema === 'dark' ? 'dark' : 'light')
})
it('perfil guarda nombre y permite cerrar sesión', async () => {
  useAutenticacionStore().usuario = usuario
  cuenta.actualizar.mockResolvedValue({ data: { ...usuario, nombre: 'Actualizada' } })
  cuenta.salir.mockResolvedValue({ status: 204 })
  const w = montar(PerfilView)
  await w.get('#nombre').setValue('Actualizada')
  await w.get('form').trigger('submit'); await flushPromises()
  expect(w.text()).toContain('Cambios guardados.')
  await w.get('#nombre').setValue('')
  await w.findAll('button').find((b) => b.text() === 'Cerrar sesión').trigger('click')
  await flushPromises()
  expect(useAutenticacionStore().usuario).toBeNull()
  expect(replace).toHaveBeenCalledWith('/ingresar')
})
it('restablecimiento envía el token del enlace y una nueva contraseña', async () => {
  cuenta.restablecer.mockResolvedValue({ data: {} })
  const w = montar(EnlaceView)
  await w.get('#contrasena').setValue('Nueva-segura123!')
  await w.get('#confirmacion').setValue('Nueva-segura123!')
  await w.get('form').trigger('submit'); await flushPromises()
  expect(cuenta.restablecer).toHaveBeenCalledWith({ uid: 'MQ', token: 'prueba', contrasena: 'Nueva-segura123!' })
  expect(w.get('[role="status"]').text()).toContain('Contraseña actualizada')
})
it('Google muestra configuración pendiente sin fingir autenticación', async () => {
  cuenta.google.mockRejectedValue({ response: { data: { detail: 'Google pendiente de configuración.' } } })
  const w = montar(IngresarView)
  await w.findAll('button').find((b) => b.text() === 'Continuar con Google').trigger('click')
  await flushPromises()
  expect(w.get('[role="alert"]').text()).toBe('Google pendiente de configuración.')
})
