import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { flushPromises, mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import api from '@/shared/services/api'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import GestionCanchasPanel from '@/modules/canchas/components/GestionCanchasPanel.vue'
import FormularioCancha from '@/modules/canchas/components/FormularioCancha.vue'
import { canchasApi } from '@/modules/canchas/services/canchas'

vi.mock('@/shared/services/api', () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}))

const sedes = [
  { id: 4, nombre: 'Complejo Amarilis' },
  { id: 9, nombre: 'Sede Centro' },
]
const cancha = {
  id: 21, sede: 'Complejo Amarilis', sede_id: 4, empresa: 'Club Deportivo', empresa_id: 2,
  nombre: 'Cancha 1', descripcion: 'Campo principal',
  modalidad: 7, tipo_superficie: 'Sintético', capacidad_jugadores: 14,
  techada: false, iluminacion: true, caracteristicas: ['Tribuna', 'Vestuarios'],
  estado: 'activa', imagen_principal_url: '/media/canchas/21.jpg', imagenes: [],
}
const paginaCon = (results = [cancha], count = results.length) => ({
  data: { count, next: null, previous: null, results },
})

beforeEach(() => {
  vi.resetAllMocks()
  localStorage.clear()
  window.confirm = vi.fn(() => true)
  api.get.mockResolvedValue(paginaCon())
  api.post.mockResolvedValue({ data: cancha })
  api.patch.mockResolvedValue({ data: cancha })
})

function montarPanel(props = {}) {
  return mount(GestionCanchasPanel, { props: { sedes, ...props } })
}

describe('servicio de canchas', () => {
  it('usa los endpoints acordados para estado e imágenes', async () => {
    await canchasApi.cambiarEstado(21, 'mantenimiento')
    expect(api.post).toHaveBeenCalledWith('/canchas/21/estado/', {
      estado: 'mantenimiento', confirmar: true,
    })

    const archivo = new File(['foto'], 'cancha.png', { type: 'image/png' })
    await canchasApi.subirImagen(21, { archivo, descripcion: 'Vista lateral', orden: 2 })
    const [url, datos] = api.post.mock.calls[1]
    expect(url).toBe('/canchas/21/imagenes/')
    expect(datos.get('archivo')).toBe(archivo)
    expect(datos.get('descripcion')).toBe('Vista lateral')
    expect(datos.get('orden')).toBe('2')

    await canchasApi.retirarImagen(21, 88)
    expect(api.post).toHaveBeenLastCalledWith('/canchas/21/imagenes/88/retirar/', { confirmar: true })
  })
})

describe('listado y filtros', () => {
  it('muestra cancha, sede, estado y características', async () => {
    const wrapper = montarPanel()
    await flushPromises()
    expect(wrapper.text()).toContain('Cancha 1')
    expect(wrapper.text()).toContain('Complejo Amarilis')
    expect(wrapper.text()).toContain('Fútbol 7')
    expect(wrapper.text()).toContain('Mantenimiento')
    expect(wrapper.text()).toContain('Tribuna')
    wrapper.unmount()
  })

  it('envía sede, modalidad, estado y búsqueda al API', async () => {
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.get('select[aria-label="Filtrar por sede"]').setValue('9')
    await wrapper.find('input[aria-label="Filtrar por modalidad"]').setValue('11')
    await wrapper.get('select[aria-label="Filtrar por estado"]').setValue('mantenimiento')
    await wrapper.find('input[placeholder="Buscar cancha"]').setValue('Cancha norte')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('/canchas/', { params: {
      page: 1, page_size: 12, sede: '9', modalidad: 11, estado: 'mantenimiento', buscar: 'Cancha norte',
    } })
    wrapper.unmount()
  })

  it('pagina resultados con el conteo DRF', async () => {
    api.get.mockResolvedValue(paginaCon([cancha], 25))
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.findAll('button').find((boton) => boton.text().includes('Siguiente')).trigger('click')
    await flushPromises()
    expect(api.get).toHaveBeenLastCalledWith('/canchas/', { params: { page: 2, page_size: 12 } })
    expect(wrapper.text()).toContain('Página 2 de 3')
    wrapper.unmount()
  })

  it('presenta loading, estado vacío y error de carga', async () => {
    let completar
    api.get.mockReturnValueOnce(new Promise((resolveApi) => { completar = resolveApi }))
    const cargando = montarPanel()
    await nextTick()
    expect(cargando.get('[role="status"]').text()).toContain('Cargando canchas')
    completar(paginaCon([], 0))
    await flushPromises()
    expect(cargando.text()).toContain('Todavía no hay canchas registradas.')
    cargando.unmount()

    api.get.mockRejectedValueOnce({ response: { data: { detail: 'Sede no autorizada.' } } })
    const fallida = montarPanel()
    await flushPromises()
    expect(fallida.get('[role="alert"]').text()).toBe('Sede no autorizada.')
    fallida.unmount()
  })
})

describe('alta, edición y estado operativo', () => {
  it('valida campos requeridos y anuncia errores junto a cada campo', async () => {
    const wrapper = mount(FormularioCancha, { props: { sedes } })
    await wrapper.get('form').trigger('submit')
    expect(wrapper.get('[role="alert"]').text()).toContain('Revisa estos datos')
    expect(wrapper.get('#cancha-nombre').attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('#cancha-modalidad').attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('#cancha-tipo_superficie').attributes('aria-invalid')).toBe('true')
    expect(wrapper.emitted('guardar')).toBeUndefined()
    wrapper.unmount()
  })

  it('permite guardar sin capacidad recomendada y envía null', async () => {
    const wrapper = mount(FormularioCancha, { props: { sedes } })
    await wrapper.get('#cancha-sede_id').setValue('4')
    await wrapper.get('#cancha-nombre').setValue('Cancha sin aforo definido')
    await wrapper.get('#cancha-modalidad').setValue('5')
    await wrapper.get('#cancha-tipo_superficie').setValue('Sintético')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('guardar')[0][0].datos.capacidad_jugadores).toBeNull()
    wrapper.unmount()
  })

  it('registra una cancha con modalidad numérica y características', async () => {
    api.get.mockResolvedValueOnce(paginaCon([]))
    api.post.mockResolvedValueOnce({ data: { ...cancha, id: 22, nombre: 'Cancha Nueva' } })
      .mockResolvedValueOnce({ data: {} })
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.get('button[aria-label="Nueva cancha"]').trigger('click')
    await wrapper.get('#cancha-sede_id').setValue('4')
    await wrapper.get('#cancha-nombre').setValue('Cancha Nueva')
    await wrapper.get('#cancha-modalidad').setValue('8')
    await wrapper.get('#cancha-tipo_superficie').setValue('Cemento')
    await wrapper.get('#cancha-capacidad_jugadores').setValue('16')
    await wrapper.get('#cancha-caracteristicas').setValue('Tribuna\nVestuarios')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.post).toHaveBeenCalledWith('/canchas/', expect.objectContaining({
      sede_id: 4, nombre: 'Cancha Nueva', modalidad: 8, capacidad_jugadores: 16,
      tipo_superficie: 'Cemento', caracteristicas: ['Tribuna', 'Vestuarios'],
    }))
    expect(wrapper.get('[role="status"]').text()).toContain('Cancha guardada.')
    wrapper.unmount()
  })

  it('edita datos existentes y mantiene sus valores iniciales', async () => {
    api.patch.mockResolvedValueOnce({ data: { ...cancha, nombre: 'Cancha renovada' } })
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.get('[aria-label="Editar Cancha 1"]').trigger('click')
    expect(wrapper.get('#cancha-modalidad').element.value).toBe('7')
    await wrapper.get('#cancha-nombre').setValue('Cancha renovada')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(api.patch).toHaveBeenCalledWith('/canchas/21/', expect.objectContaining({ nombre: 'Cancha renovada' }))
    expect(api.patch.mock.calls[0][1]).not.toHaveProperty('sede_id')
    wrapper.unmount()
  })

  it('muestra errores de validación de API ligados al campo', async () => {
    api.get.mockResolvedValueOnce(paginaCon([]))
    api.post.mockRejectedValueOnce({ response: { data: { nombre: ['Ya existe una cancha con ese nombre.'] } } })
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.get('button[aria-label="Nueva cancha"]').trigger('click')
    await wrapper.get('#cancha-sede_id').setValue('4')
    await wrapper.get('#cancha-nombre').setValue('Cancha Nueva')
    await wrapper.get('#cancha-modalidad').setValue('5')
    await wrapper.get('#cancha-tipo_superficie').setValue('Sintético')
    await wrapper.get('#cancha-capacidad_jugadores').setValue('10')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(wrapper.get('#cancha-nombre').attributes('aria-invalid')).toBe('true')
    expect(wrapper.get('[role="alert"]').text()).toContain('Ya existe una cancha con ese nombre.')
    wrapper.unmount()
  })

  it('confirma y aplica cambios de estado sin llamarlo disponibilidad', async () => {
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.get('[aria-label="Nuevo estado de Cancha 1"]').setValue('mantenimiento')
    await wrapper.get('[aria-label="Aplicar estado a Cancha 1"]').trigger('click')
    await flushPromises()
    expect(window.confirm).toHaveBeenCalledWith('¿Cambiar el estado de Cancha 1 a mantenimiento?')
    expect(api.post).toHaveBeenCalledWith('/canchas/21/estado/', { estado: 'mantenimiento', confirmar: true })
    expect(wrapper.text()).toContain('Estado de Cancha 1 actualizado.')
    wrapper.unmount()
  })

  it('sube y retira fotografías de la galería con confirmación', async () => {
    const wrapper = montarPanel()
    await flushPromises()
    const input = wrapper.get('input[type="file"]')
    const archivo = new File(['foto'], 'lateral.webp', { type: 'image/webp' })
    Object.defineProperty(input.element, 'files', { value: [archivo], configurable: true })
    await input.trigger('change')
    await wrapper.findAll('label').find((label) => label.text().includes('Descripción de la imagen')).get('input').setValue('Vista lateral')
    await wrapper.findAll('form').find((form) => form.text().includes('Añadir fotografía')).trigger('submit')
    await flushPromises()
    const [url, datos] = api.post.mock.calls[0]
    expect(url).toBe('/canchas/21/imagenes/')
    expect(datos.get('archivo')).toBe(archivo)
    expect(datos.get('descripcion')).toBe('Vista lateral')

    wrapper.unmount()
  })

  it('retira una fotografía solo tras confirmar la acción', async () => {
    api.get.mockResolvedValueOnce(paginaCon([{ ...cancha, imagenes: [{ id: 88, url: '/foto.jpg' }] }]))
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.get('[aria-label="Retirar fotografía 1 de Cancha 1"]').trigger('click')
    await flushPromises()
    expect(window.confirm).toHaveBeenCalledWith('¿Retirar esta fotografía de Cancha 1?')
    expect(api.post).toHaveBeenCalledWith('/canchas/21/imagenes/88/retirar/', { confirmar: true })
    wrapper.unmount()
  })

  it('actualiza la foto principal después de guardar una cancha nueva', async () => {
    api.get.mockResolvedValueOnce(paginaCon([]))
    api.post.mockResolvedValueOnce({ data: { ...cancha, id: 22 } })
    const wrapper = montarPanel()
    await flushPromises()
    await wrapper.get('button[aria-label="Nueva cancha"]').trigger('click')
    await wrapper.get('#cancha-sede_id').setValue('4')
    await wrapper.get('#cancha-nombre').setValue('Cancha con foto')
    await wrapper.get('#cancha-modalidad').setValue('5')
    await wrapper.get('#cancha-tipo_superficie').setValue('Sintético')
    await wrapper.get('#cancha-capacidad_jugadores').setValue('10')
    const input = wrapper.get('#cancha-imagen_principal')
    const archivo = new File(['foto'], 'portada.png', { type: 'image/png' })
    Object.defineProperty(input.element, 'files', { value: [archivo], configurable: true })
    await input.trigger('change')
    await wrapper.findAll('form').find((form) => form.text().includes('Registrar cancha')).trigger('submit')
    await flushPromises()
    const [url, datos] = api.patch.mock.calls[0]
    expect(url).toBe('/canchas/22/')
    expect(datos.get('imagen_principal')).toBe(archivo)
    wrapper.unmount()
  })
})

describe('permisos de interfaz, imágenes y temas', () => {
  it('mantiene la consulta del cajero en solo lectura', async () => {
    const wrapper = montarPanel({ soloLectura: true })
    await flushPromises()
    expect(wrapper.find('button[aria-label="Nueva cancha"]').exists()).toBe(false)
    expect(wrapper.find('button[aria-label="Editar Cancha 1"]').exists()).toBe(false)
    expect(wrapper.find('select[aria-label="Nuevo estado de Cancha 1"]').exists()).toBe(false)
    expect(wrapper.find('input[type="file"]').exists()).toBe(false)
    wrapper.unmount()
  })

  it('rechaza en la interfaz tipos de archivo no admitidos', async () => {
    const wrapper = montarPanel()
    await flushPromises()
    const input = wrapper.get('input[type="file"]')
    const archivo = new File(['texto'], 'notas.txt', { type: 'text/plain' })
    Object.defineProperty(input.element, 'files', { value: [archivo], configurable: true })
    await input.trigger('change')
    expect(wrapper.get('[role="alert"]').text()).toContain('Elige una imagen PNG, JPG o WebP válida.')
    wrapper.unmount()
  })

  it('traduce estados de cancha con tonos semánticos para ambos temas', () => {
    const inactiva = mount(EstadoEtiqueta, { props: { estado: 'inactiva' } })
    const mantenimiento = mount(EstadoEtiqueta, { props: { estado: 'mantenimiento' } })
    const tokens = readFileSync(resolve('src/shared/styles/tokens.css'), 'utf8')
    expect(inactiva.text()).toBe('Inactiva')
    expect(inactiva.classes()).toContain('admin-state-info')
    expect(mantenimiento.text()).toBe('Mantenimiento')
    expect(mantenimiento.classes()).toContain('admin-state-warning')
    expect(tokens).toContain("html[data-theme='dark']")
    expect(tokens).toContain('--status-warning-bg: #FFF1CC')
    expect(tokens).toContain('--status-warning-bg: #3A2B12')
    inactiva.unmount()
    mantenimiento.unmount()
  })
})
