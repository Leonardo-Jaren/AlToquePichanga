<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import AdminLayout from '@/modules/administracion/components/AdminLayout.vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { useEmpresasStore } from '../stores/empresas'
import { empresasApi } from '../services/empresas'
import DatosEmpresaPanel from '../components/DatosEmpresaPanel.vue'
import SedesPanel from '../components/SedesPanel.vue'
import EquipoPanel from '../components/EquipoPanel.vue'
import SuscripcionPanel from '../components/SuscripcionPanel.vue'
import GestionCanchasPanel from '@/modules/canchas/components/GestionCanchasPanel.vue'
import GestionHorariosPanel from '@/modules/horarios/components/GestionHorariosPanel.vue'

const store = useEmpresasStore()
const seccion = ref('resumen')
const cargando = ref(true)
const mostrandoAlta = ref(false)
const error = ref('')
const altaError = ref('')
const nombre = ref('')
const razon = ref('')
const ruc = ref('')
const resumenSuscripcion = ref(null)
const sedesEmpresa = ref([])
const menu = [
  { id: 'resumen', nombre: 'Resumen' },
  { id: 'empresa', nombre: 'Datos de empresa' },
  { id: 'sedes', nombre: 'Sedes' },
  { id: 'canchas', nombre: 'Canchas' },
  { id: 'horarios', nombre: 'Horarios' },
  { id: 'equipo', nombre: 'Equipo' },
  { id: 'suscripcion', nombre: 'Suscripción' },
]
const empresa = computed(() => store.empresaActiva)
const titulo = computed(() => ({
  resumen: 'Tu empresa, al mando',
  empresa: 'Datos de la empresa',
  sedes: 'Sedes de tu empresa',
  canchas: 'Canchas de tu empresa',
  horarios: 'Horarios y cierres',
  equipo: 'Personas y accesos',
  suscripcion: 'Plan de plataforma',
}[seccion.value]))
const descripcion = computed(() => ({
  resumen: 'Consulta el estado de aprobación, sedes y suscripción.',
  empresa: 'Mantén actualizados los datos de contacto y presentación.',
  sedes: 'Organiza la información independiente de cada complejo.',
  canchas: 'Administra las instalaciones de todas las sedes de tu empresa.',
  horarios: 'Configura horarios semanales, cierres y cambios para tus sedes y canchas.',
  equipo: 'Asigna roles y autoriza únicamente las sedes necesarias.',
  suscripcion: 'Consulta los periodos registrados y solicita activación o renovación.',
}[seccion.value]))

onMounted(cargar)
watch(() => store.activaId, cargarResumen)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    await store.cargar()
    await cargarResumen()
  } catch {
    error.value = 'No se pudieron cargar tus empresas.'
  } finally {
    cargando.value = false
  }
}
async function cargarResumen() {
  resumenSuscripcion.value = null
  sedesEmpresa.value = []
  if (!store.activaId) return
  const [suscripcion, sedes] = await Promise.allSettled([
    empresasApi.suscripcion(store.activaId),
    empresasApi.listarSedes(store.activaId),
  ])
  if (suscripcion.status === 'fulfilled') resumenSuscripcion.value = suscripcion.value.data
  if (sedes.status === 'fulfilled') sedesEmpresa.value = sedes.value.data
}
async function cargarSedes() {
  if (!store.activaId) return
  try {
    sedesEmpresa.value = (await empresasApi.listarSedes(store.activaId)).data
  } catch {
    sedesEmpresa.value = []
  }
}
function cambiarSeccion(valor) {
  seccion.value = valor
  if (valor === 'equipo' || valor === 'canchas' || valor === 'horarios') cargarSedes()
}
async function crearEmpresa() {
  altaError.value = ''
  try {
    await store.registrar({ razon_social: razon.value, nombre_comercial: nombre.value, ruc: ruc.value })
    mostrandoAlta.value = false
    nombre.value = ''
    razon.value = ''
    ruc.value = ''
    await cargarResumen()
  } catch (fallo) {
    altaError.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo registrar la empresa.'
  }
}
function actualizarEmpresa(datos) {
  store.lista = store.lista.map((item) => item.id === datos.id ? datos : item)
}
</script>

<template>
  <AdminLayout :titulo="titulo" :descripcion="descripcion" :secciones="menu" :activa="seccion" @cambiar-seccion="cambiarSeccion">
    <template #sidebar>
      <label v-if="store.lista.length" class="mt-5 block">
        <span class="admin-label">Empresa activa</span>
        <select class="admin-field" :value="store.activaId" @change="store.seleccionar($event.target.value)">
          <option v-for="item in store.lista" :key="item.id" :value="item.id">{{ item.nombre_comercial || item.razon_social || item.nombre }}</option>
        </select>
      </label>
    </template>

    <p v-if="error" role="alert" class="admin-error mb-4">{{ error }}</p>
    <p v-if="cargando" role="status" class="admin-card">Cargando tus empresas…</p>

    <template v-else-if="!empresa">
      <section class="admin-card max-w-3xl" aria-labelledby="alta-empresa">
        <p class="mb-2 text-sm font-semibold text-app-link">Empezar con AlToque</p>
        <h2 id="alta-empresa" class="font-display text-2xl">Registra tu empresa</h2>
        <p class="mt-3 text-sm text-app-text-muted">La nueva empresa queda pendiente hasta que la plataforma revise su activación.</p>
        <form class="mt-6 grid gap-4 sm:grid-cols-2" novalidate @submit.prevent="crearEmpresa">
          <label><span class="admin-label">Razón social *</span><input v-model.trim="razon" class="admin-field" required maxlength="180"></label>
          <label><span class="admin-label">Nombre comercial</span><input v-model.trim="nombre" class="admin-field" maxlength="160"></label>
          <label class="sm:col-span-2"><span class="admin-label">RUC <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="ruc" class="admin-field" inputmode="numeric" maxlength="11"></label>
          <p v-if="altaError" role="alert" class="admin-error sm:col-span-2">{{ altaError }}</p>
          <button class="admin-button admin-button-primary sm:col-span-2 sm:justify-self-start" :disabled="!razon && !nombre">Registrar empresa</button>
        </form>
      </section>
    </template>

    <template v-else>
      <div class="mb-5 flex flex-wrap items-center justify-between gap-3">
        <p class="font-semibold">{{ empresa.nombre_comercial || empresa.razon_social || empresa.nombre }}</p>
        <button class="admin-button admin-button-secondary" @click="mostrandoAlta = !mostrandoAlta">
          {{ mostrandoAlta ? 'Cancelar' : 'Registrar otra empresa' }}
        </button>
      </div>
      <form v-if="mostrandoAlta" class="admin-card mb-5 grid gap-4 sm:grid-cols-2" @submit.prevent="crearEmpresa">
        <label><span class="admin-label">Razón social *</span><input v-model.trim="razon" class="admin-field" required maxlength="180"></label>
        <label><span class="admin-label">Nombre comercial</span><input v-model.trim="nombre" class="admin-field" maxlength="160"></label>
        <label><span class="admin-label">RUC (opcional)</span><input v-model.trim="ruc" class="admin-field" inputmode="numeric" maxlength="11"></label>
        <p v-if="altaError" role="alert" class="admin-error sm:col-span-2">{{ altaError }}</p>
        <button class="admin-button admin-button-primary sm:col-span-2 sm:justify-self-start">Registrar empresa</button>
      </form>

      <section v-if="seccion === 'resumen'" class="space-y-5" aria-labelledby="estado-empresa">
        <article class="admin-card">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p class="text-sm text-app-text-muted">Estado de la empresa</p>
              <h2 id="estado-empresa" class="mt-1 text-xl font-bold">{{ empresa.nombre_comercial || empresa.razon_social || empresa.nombre }}</h2>
              <p class="mt-2 max-w-2xl text-sm text-app-text-muted">La aprobación de empresa y la vigencia del plan se revisan por separado.</p>
            </div>
            <EstadoEtiqueta :estado="empresa.estado" />
          </div>
          <dl class="mt-6 grid gap-4 sm:grid-cols-3">
            <div><dt class="text-sm text-app-text-muted">Sedes activas</dt><dd class="mt-1 text-2xl font-bold tabular-nums">{{ empresa.cantidad_sedes }}</dd></div>
            <div><dt class="text-sm text-app-text-muted">Suscripción</dt><dd class="mt-2"><EstadoEtiqueta :estado="resumenSuscripcion?.suscripcion?.estado || 'pendiente'" /></dd></div>
            <div><dt class="text-sm text-app-text-muted">Responsables autorizados</dt><dd class="mt-1 text-2xl font-bold tabular-nums">{{ empresa.responsables?.length || 0 }}</dd></div>
          </dl>
          <p v-if="empresa.estado !== 'activa'" class="mt-5 rounded-xl bg-[var(--status-warning-bg)] p-4 text-sm text-[var(--status-warning-text)]">
            Tu acceso administrativo seguirá disponible para consultar el estado y solicitar una revisión.
          </p>
        </article>
        <section v-if="empresa.responsables?.length" class="admin-card" aria-labelledby="responsables">
          <h3 id="responsables" class="font-bold">Propietarios autorizados</h3>
          <ul class="mt-3 space-y-2">
            <li v-for="persona in empresa.responsables" :key="persona.id" class="break-words text-sm">
              {{ persona.nombre || 'Propietario' }} <span class="text-app-text-muted">· {{ persona.correo }}</span>
            </li>
          </ul>
        </section>
      </section>

      <DatosEmpresaPanel v-else-if="seccion === 'empresa'" :empresa="empresa" @guardada="actualizarEmpresa" />
      <SedesPanel v-else-if="seccion === 'sedes'" :key="empresa.id" :empresa="empresa" :suscripcion="resumenSuscripcion?.suscripcion" />
      <GestionCanchasPanel v-else-if="seccion === 'canchas'" :key="'canchas-' + empresa.id" :sedes="sedesEmpresa" />
      <GestionHorariosPanel v-else-if="seccion === 'horarios'" :key="'horarios-' + empresa.id" :sedes="sedesEmpresa" />
      <EquipoPanel v-else-if="seccion === 'equipo'" :key="'equipo-' + empresa.id" :empresa="empresa" :sedes="sedesEmpresa" :suscripcion="resumenSuscripcion?.suscripcion" />
      <SuscripcionPanel v-else :key="'plan-' + empresa.id" :empresa="empresa" />
    </template>
  </AdminLayout>
</template>
