import { beforeEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DatosEmpresaPanel from '@/modules/empresas/components/DatosEmpresaPanel.vue'
import EquipoPanel from '@/modules/empresas/components/EquipoPanel.vue'
import SedesPanel from '@/modules/empresas/components/SedesPanel.vue'
import SuscripcionPanel from '@/modules/empresas/components/SuscripcionPanel.vue'
import EmpresasPlataformaPanel from '@/modules/administracion/components/EmpresasPlataformaPanel.vue'
import PlanesPanel from '@/modules/administracion/components/PlanesPanel.vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { empresasApi, plataformaApi } from '@/modules/empresas/services/empresas'
import { useEmpresasStore } from '@/modules/empresas/stores/empresas'
import { formatearDinero } from '@/shared/services/dinero'

const tokens = readFileSync(resolve('src/shared/styles/tokens.css'), 'utf8')
const adminStyles = readFileSync(resolve('src/modules/administracion/admin.css'), 'utf8')

vi.mock('@/modules/empresas/services/empresas', () => ({
  empresasApi: {
    listar: vi.fn(), registrar: vi.fn(), detalle: vi.fn(), actualizar: vi.fn(),
    actualizarLogo: vi.fn(), listarSedes: vi.fn(), crearSede: vi.fn(),
    actualizarSede: vi.fn(), estadoSede: vi.fn(), imagenSede: vi.fn(),
    retirarImagenSede: vi.fn(), listarPersonal: vi.fn(), invitarPersonal: vi.fn(),
    revocarPersonal: vi.fn(), revocarInvitacion: vi.fn(), planes: vi.fn(),
    suscripcion: vi.fn(), solicitarSuscripcion: vi.fn(), aceptarInvitacion: vi.fn(),
  },
  plataformaApi: {
    empresas: vi.fn(), detalleEmpresa: vi.fn(), estadoEmpresa: vi.fn(),
    planes: vi.fn(), guardarPlan: vi.fn(), solicitudes: vi.fn(),
    resolverSolicitud: vi.fn(), estadoSuscripcion: vi.fn(), configuracion: vi.fn(),
    guardarConfiguracion: vi.fn(),
  },
}))

const empresa = {
  id: 8, nombre: 'Complejos Huánuco', razon_social: 'Complejos Huánuco SAC',
  nombre_comercial: 'Huánuco Fútbol', activa: true, estado: 'activa',
}
const plan = {
  id: 3, nombre: 'Inicial', descripcion: 'Plan configurable', precio: '120.00',
  moneda: 'PEN', frecuencia: 'mensual', maximo_sedes: 2, maximo_empleados: 5,
  maximo_canchas: null, activo: true,
}

beforeEach(() => {
  setActivePinia(createPinia())
  localStorage.clear()
  vi.resetAllMocks()
  window.confirm = vi.fn(() => true)
})

describe('Empresas y selector activo', () => {
  it('carga páginas, restaura la empresa seleccionada y persiste el cambio', async () => {
    const filas = Array.from({ length: 100 }, (_, indice) => ({ id: indice + 1 }))
    localStorage.setItem('altoque.empresa-activa', '101')
    empresasApi.listar
      .mockResolvedValueOnce({ data: { count: 101, results: filas } })
      .mockResolvedValueOnce({ data: { count: 101, results: [{ id: 101 }] } })
    const store = useEmpresasStore()

    await store.cargar()

    expect(empresasApi.listar).toHaveBeenCalledTimes(2)
    expect(store.empresaActiva.id).toBe(101)
    store.seleccionar(1)
    expect(localStorage.getItem('altoque.empresa-activa')).toBe('1')
  })

  it('muestra error de carga y termina el estado ocupado', async () => {
    empresasApi.listar.mockRejectedValue(new Error('Sin conexión'))
    const store = useEmpresasStore()

    await expect(store.cargar()).rejects.toThrow('No se pudieron cargar tus empresas.')
    expect(store.error).toBe('No se pudieron cargar tus empresas.')
    expect(store.cargando).toBe(false)
  })

  it('mantiene estados semánticos y tokens disponibles en claro y oscuro', () => {
    const wrapper = mount(EstadoEtiqueta, { props: { estado: 'pendiente' } })
    expect(wrapper.classes()).toContain('admin-state-warning')
    expect(tokens).toContain("html[data-theme='dark']")
    expect(tokens).toContain('--status-warning-bg: #FFF1CC')
    expect(tokens).toContain('--status-warning-bg: #3A2B12')
    expect(adminStyles).toContain('background: var(--status-warning-bg)')
    expect(adminStyles).toContain('color: var(--text)')
  })

  it('busca y muestra empresas en el panel de plataforma', async () => {
    plataformaApi.empresas.mockResolvedValue({ data: {
      count: 1, results: [{ ...empresa, responsables: [{ id: 1, correo: 'duena@example.com' }],
        cantidad_sedes: 0, suscripcion: null }],
    } })
    const wrapper = mount(EmpresasPlataformaPanel)
    await flushPromises()
    expect(wrapper.text()).toContain('Huánuco Fútbol')
    expect(wrapper.text()).toContain('Pendiente')

    await wrapper.find('input').setValue('Huánuco')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(plataformaApi.empresas).toHaveBeenLastCalledWith({ page: 1, q: 'Huánuco', estado: '' })
  })
})

describe('Empresa y sedes', () => {
  it('guarda cambios de empresa y anuncia el resultado', async () => {
    empresasApi.actualizar.mockResolvedValue({ data: { ...empresa, nombre_comercial: 'Huánuco Nuevo' } })
    const wrapper = mount(DatosEmpresaPanel, { props: { empresa } })
    await wrapper.find('#nombre_comercial').setValue('Huánuco Nuevo')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(empresasApi.actualizar).toHaveBeenCalledWith(empresa.id, expect.objectContaining({
      nombre_comercial: 'Huánuco Nuevo',
    }))
    expect(wrapper.emitted('guardada')[0][0].nombre_comercial).toBe('Huánuco Nuevo')
    expect(wrapper.get('[role="status"]').text()).toContain('Datos de la empresa guardados.')
  })

  it('muestra campos rechazados por el servidor', async () => {
    empresasApi.actualizar.mockRejectedValue({ response: { data: { ruc: ['RUC duplicado.'] } } })
    const wrapper = mount(DatosEmpresaPanel, { props: { empresa } })
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(wrapper.text()).toContain('RUC duplicado.')
    expect(wrapper.get('[role="alert"]').exists()).toBe(true)
  })

  it('presenta vacío y bloquea crear sedes sin empresa aprobada y suscripción', async () => {
    empresasApi.listarSedes.mockResolvedValue({ data: [] })
    const wrapper = mount(SedesPanel, {
      props: { empresa: { ...empresa, activa: false }, suscripcion: { estado: 'activa' } },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Todavía no hay sedes registradas.')
    expect(wrapper.get('button').element.disabled).toBe(true)
  })

  it('crea una sede desde el formulario cuando la cuenta tiene acceso operativo', async () => {
    empresasApi.listarSedes.mockResolvedValue({ data: [] })
    empresasApi.crearSede.mockResolvedValue({ data: {
      id: 22, empresa_id: empresa.id, nombre: 'Sede Centro', direccion: 'Av. Lima 10',
      activa: true, horario_general: {}, imagenes: [],
    } })
    const wrapper = mount(SedesPanel, { props: { empresa, suscripcion: { estado: 'activa' } } })
    await flushPromises()
    await wrapper.get('button').trigger('click')
    const formulario = wrapper.get('form')
    const nombre = wrapper.findAll('label').find((label) => label.text().includes('Nombre *'))
    const direccion = wrapper.findAll('label').find((label) => label.text().includes('Dirección *'))
    await nombre.get('input').setValue('Sede Centro')
    await direccion.get('input').setValue('Av. Lima 10')
    await formulario.trigger('submit')
    await flushPromises()

    expect(empresasApi.crearSede).toHaveBeenCalledWith(expect.objectContaining({
      empresa_id: empresa.id, nombre: 'Sede Centro', direccion: 'Av. Lima 10',
    }))
    expect(wrapper.text()).toContain('Sede guardada.')
  })
})

describe('Equipo, planes y suscripciones', () => {
  it('restringe invitaciones operativas hasta aprobar empresa y suscripción', async () => {
    empresasApi.listarPersonal.mockResolvedValue({ data: { personal: [], invitaciones: [] } })
    const wrapper = mount(EquipoPanel, {
      props: { empresa: { ...empresa, activa: false }, sedes: [{ id: 2, nombre: 'Centro', activa: true }] },
    })
    await flushPromises()
    expect(wrapper.text()).toContain('La empresa necesita aprobación y una suscripción vigente')
    expect(wrapper.get('form button').element.disabled).toBe(true)
  })

  it('asigna un rol de sede con las sedes que seleccionó el usuario', async () => {
    empresasApi.listarPersonal.mockResolvedValue({ data: { personal: [], invitaciones: [] } })
    empresasApi.invitarPersonal.mockResolvedValue({ data: { tipo: 'invitacion' } })
    const sede = { id: 12, nombre: 'Amarilis', distrito: 'Amarilis', activa: true }
    const wrapper = mount(EquipoPanel, {
      props: { empresa, sedes: [sede], suscripcion: { estado: 'activa' } },
    })
    await flushPromises()
    await wrapper.get('input[type="email"]').setValue('empleado@example.com')
    await wrapper.get('select').setValue('administrador_sede')
    await wrapper.get('input[type="checkbox"]').setValue(true)
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(empresasApi.invitarPersonal).toHaveBeenCalledWith(empresa.id, {
      correo: 'empleado@example.com', rol: 'administrador_sede', sedes: [sede.id],
    })
  })

  it('muestra estado vencido, límites e historial sin habilitar una solicitud duplicada', async () => {
    empresasApi.suscripcion.mockResolvedValue({ data: {
      suscripcion: { estado: 'vencida', plan, importe_acordado: '120.00',
        moneda_acordada: 'PEN', frecuencia_acordada: 'mensual', fecha_inicio: '2026-01-01',
        fecha_vencimiento: '2026-01-31', periodos: [{ plan: 'Inicial', fecha_inicio: '2026-01-01',
          fecha_vencimiento: '2026-01-31', importe: '120.00', moneda: 'PEN' }] },
      solicitudes: [{ id: 1, estado: 'pendiente', plan: 'Inicial', tipo: 'activacion',
        precio: '120.00', moneda: 'PEN', creada_en: '2026-01-01T10:00:00Z' }],
    } })
    empresasApi.planes.mockResolvedValue({ data: [plan] })
    const wrapper = mount(SuscripcionPanel, { props: { empresa } })
    await flushPromises()
    expect(wrapper.text()).toContain('Vencida')
    expect(wrapper.text()).toContain('Límite de sedes activas')
    expect(wrapper.text()).toContain('Periodos registrados')
    expect(wrapper.text()).toContain('Hay una solicitud pendiente.')
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('permite editar un plan y conserva límites vacíos como valores configurables', async () => {
    plataformaApi.planes.mockResolvedValue({ data: [{ ...plan, maximo_sedes: null }] })
    plataformaApi.guardarPlan.mockResolvedValue({ data: { ...plan } })
    const wrapper = mount(PlanesPanel)
    await flushPromises()
    expect(wrapper.text()).toContain('Sin límite configurado')
    await wrapper.get('button').trigger('click')
    await wrapper.findAll('label').find((label) => label.text().includes('Nombre *'))
      .get('input').setValue('Plan Empresarial')
    await wrapper.findAll('label').find((label) => label.text().includes('Precio *'))
      .get('input').setValue('240.50')
    await wrapper.get('form').trigger('submit')
    await flushPromises()
    expect(plataformaApi.guardarPlan).toHaveBeenCalledWith(expect.objectContaining({
      nombre: 'Plan Empresarial', precio: '240.50', maximo_sedes: null,
    }), null)
  })

  it('formatea dinero desde texto sin perder centavos grandes', () => {
    expect(formatearDinero('123456789012.34', 'PEN')).toContain('123,456,789,012.34')
    expect(formatearDinero('12.50', 'ZZ!')).toBe('ZZ! 12.50')
  })
})
