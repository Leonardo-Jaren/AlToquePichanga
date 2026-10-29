<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ChevronLeft, ChevronRight, Plus, Search } from 'lucide-vue-next'
import CanchaCard from './CanchaCard.vue'
import FormularioCancha from './FormularioCancha.vue'
import { canchasApi } from '../services/canchas'

const props = defineProps({
  sedes: { type: Array, default: () => [] },
  sedeInicialId: { type: [Number, String], default: '' },
  sedeFija: { type: Boolean, default: false },
  soloLectura: { type: Boolean, default: false },
  cargarSedes: { type: Boolean, default: false },
})

const sedesInternas = ref([])
const filtros = reactive({ sede: '', modalidad: '', estado: '', buscar: '' })
const canchas = ref([])
const total = ref(0)
const pagina = ref(1)
const tamanoPagina = 12
const cargando = ref(false)
const guardando = ref(false)
const error = ref('')
const mensaje = ref('')
const erroresFormulario = ref({})
const mostrarFormulario = ref(false)
const canchaEditando = ref(null)
const subiendoImagenId = ref(null)
const retirandoImagenId = ref(null)
const sedesDisponibles = computed(() => (props.cargarSedes ? sedesInternas.value : props.sedes))
const paginas = computed(() => Math.max(1, Math.ceil(total.value / tamanoPagina)))
const sedeNombrePorId = computed(() => new Map(sedesDisponibles.value.map((sede) => [Number(sede.id), sede.nombre])))
let peticion = 0
let inicializado = false

onMounted(iniciar)
watch(() => props.sedeInicialId, async (id) => {
  filtros.sede = id ? String(id) : ''
  if (inicializado) await cargar(1)
})

async function iniciar() {
  if (props.cargarSedes) {
    try {
      const { data } = await canchasApi.listarSedes()
      sedesInternas.value = Array.isArray(data) ? data : data.results || []
    } catch (fallo) {
      error.value = fallo.response?.data?.detail || 'No se pudieron cargar las sedes autorizadas.'
    }
  }
  filtros.sede = props.sedeInicialId ? String(props.sedeInicialId) : ''
  inicializado = true
  await cargar(1)
}

function parametrosListado(numeroPagina) {
  const params = { page: numeroPagina, page_size: tamanoPagina }
  if (filtros.sede) params.sede = filtros.sede
  if (filtros.modalidad) params.modalidad = filtros.modalidad
  if (filtros.estado) params.estado = filtros.estado
  if (filtros.buscar.trim()) params.buscar = filtros.buscar.trim()
  return params
}

async function cargar(numeroPagina = pagina.value) {
  const actual = ++peticion
  cargando.value = true
  error.value = ''
  try {
    const { data } = await canchasApi.listar(parametrosListado(numeroPagina))
    if (actual !== peticion) return
    const respuesta = Array.isArray(data) ? { count: data.length, results: data } : data
    canchas.value = respuesta.results || []
    total.value = Number(respuesta.count) || 0
    pagina.value = numeroPagina
  } catch (fallo) {
    if (actual !== peticion) return
    error.value = fallo.response?.data?.detail || 'No se pudieron cargar las canchas. Vuelve a intentarlo.'
  } finally {
    if (actual === peticion) cargando.value = false
  }
}

function buscar() { cargar(1) }
function nuevaCancha() {
  erroresFormulario.value = {}
  canchaEditando.value = null
  mensaje.value = ''
  mostrarFormulario.value = true
}
function editarCancha(cancha) {
  erroresFormulario.value = {}
  canchaEditando.value = cancha
  mensaje.value = ''
  mostrarFormulario.value = true
}
function cancelarFormulario() {
  if (guardando.value) return
  mostrarFormulario.value = false
  canchaEditando.value = null
  erroresFormulario.value = {}
}

function normalizarErrores(fallo) {
  const data = fallo.response?.data
  if (data && typeof data === 'object') {
    const errores = {}
    Object.entries(data).forEach(([campo, valor]) => {
      errores[campo] = Array.isArray(valor) ? valor.map(String).join(' ') : String(valor)
    })
    if (!Object.keys(errores).length) errores.detail = 'No se pudo guardar la cancha.'
    return errores
  }
  return { detail: 'No se pudo guardar la cancha. Revisa la conexión e inténtalo nuevamente.' }
}

async function guardarCancha({ datos, imagenPrincipal }) {
  if (datos.publicada && !canchaEditando.value?.publicada
    && !window.confirm('La cancha y sus horarios y precios visibles se mostrarán en la consulta pública. ¿Quieres publicarla?')) return
  guardando.value = true
  error.value = ''
  mensaje.value = ''
  erroresFormulario.value = {}
  let guardada
  try {
    let respuesta
    if (canchaEditando.value) {
      const datosEdicion = { ...datos }
      delete datosEdicion.sede_id
      respuesta = await canchasApi.actualizar(canchaEditando.value.id, datosEdicion)
    } else {
      respuesta = await canchasApi.crear(datos)
    }
    guardada = respuesta.data
    if (imagenPrincipal) {
      try {
        guardada = (await canchasApi.actualizarImagenPrincipal(guardada.id, imagenPrincipal)).data
      } catch {
        canchaEditando.value = guardada
        erroresFormulario.value = { detail: 'La cancha se guardó, pero no se pudo subir la imagen principal. Selecciónala e inténtalo de nuevo.' }
        await cargar(pagina.value)
        return
      }
    }
    canchaEditando.value = null
    mostrarFormulario.value = false
    mensaje.value = 'Cancha guardada.'
    await cargar(pagina.value)
  } catch (fallo) {
    erroresFormulario.value = normalizarErrores(fallo)
  } finally {
    guardando.value = false
  }
}

async function cambiarEstado({ cancha, estado }) {
  if (!window.confirm(`¿Cambiar el estado de ${cancha.nombre} a ${estado}?`)) return
  error.value = ''
  mensaje.value = ''
  try {
    await canchasApi.cambiarEstado(cancha.id, estado)
    mensaje.value = `Estado de ${cancha.nombre} actualizado.`
    await cargar(pagina.value)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cambiar el estado de la cancha.'
  }
}

async function subirImagen({ cancha, archivo, descripcion, orden }) {
  error.value = ''
  mensaje.value = ''
  subiendoImagenId.value = cancha.id
  try {
    await canchasApi.subirImagen(cancha.id, { archivo, descripcion, orden })
    mensaje.value = `Fotografía añadida a ${cancha.nombre}.`
    await cargar(pagina.value)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo subir la fotografía.'
  } finally {
    subiendoImagenId.value = null
  }
}

async function retirarImagen({ cancha, imagen }) {
  if (!window.confirm(`¿Retirar esta fotografía de ${cancha.nombre}?`)) return
  error.value = ''
  mensaje.value = ''
  retirandoImagenId.value = imagen.id
  try {
    await canchasApi.retirarImagen(cancha.id, imagen.id)
    mensaje.value = 'Fotografía retirada.'
    await cargar(pagina.value)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo retirar la fotografía.'
  } finally {
    retirandoImagenId.value = null
  }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="canchas-titulo">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 id="canchas-titulo" class="text-xl font-bold">Canchas</h2>
        <p class="mt-1 text-sm text-app-text-muted">Información de las instalaciones y su estado operativo.</p>
      </div>
      <button v-if="!soloLectura" class="admin-button admin-button-primary" type="button" aria-label="Nueva cancha" :disabled="!sedesDisponibles.length" @click="nuevaCancha">
        <Plus aria-hidden="true" class="size-4" />Nueva cancha
      </button>
    </div>

    <p v-if="!sedesDisponibles.length && !cargando" class="admin-card text-sm text-app-text-muted">
      No hay sedes disponibles para consultar o asignar canchas.
    </p>
    <FormularioCancha v-if="mostrarFormulario" :key="canchaEditando?.id || 'nueva'" :cancha="canchaEditando" :sedes="sedesDisponibles" :sede-inicial-id="sedeInicialId || filtros.sede" :sede-fija="sedeFija" :guardando="guardando" :errores="erroresFormulario" @guardar="guardarCancha" @cancelar="cancelarFormulario" />

    <form class="admin-card grid gap-3 border-l-2 border-l-brand-lime md:grid-cols-2 xl:grid-cols-5" @submit.prevent="buscar">
      <label v-if="!sedeFija" class="xl:col-span-1">
        <span class="admin-label">Sede</span>
        <select v-model="filtros.sede" class="admin-field" aria-label="Filtrar por sede"><option value="">Todas las sedes</option><option v-for="sede in sedesDisponibles" :key="sede.id" :value="String(sede.id)">{{ sede.nombre }}</option></select>
      </label>
      <label>
        <span class="admin-label">Modalidad</span>
        <input v-model="filtros.modalidad" class="admin-field" type="number" min="1" step="1" inputmode="numeric" placeholder="Todas" aria-label="Filtrar por modalidad">
      </label>
      <label>
        <span class="admin-label">Estado operativo</span>
        <select v-model="filtros.estado" class="admin-field" aria-label="Filtrar por estado">
          <option value="">Todos</option><option value="activa">Activa</option><option value="inactiva">Inactiva</option><option value="mantenimiento">Mantenimiento</option>
        </select>
      </label>
      <label class="md:col-span-2 xl:col-span-1">
        <span class="admin-label">Nombre</span>
        <input v-model.trim="filtros.buscar" class="admin-field" maxlength="160" placeholder="Buscar cancha">
      </label>
      <button class="admin-button admin-button-secondary self-end" type="submit" :disabled="cargando">
        <Search aria-hidden="true" class="size-4" />{{ cargando ? 'Buscando…' : 'Buscar' }}
      </button>
    </form>

    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>
    <p v-if="cargando" role="status" class="admin-card">Cargando canchas…</p>
    <div v-else-if="!canchas.length" class="admin-card border-l-2 border-l-brand-lime">
      <h3 class="font-bold">{{ filtros.buscar || filtros.modalidad || filtros.estado ? 'No encontramos canchas con esos filtros.' : 'Todavía no hay canchas registradas.' }}</h3>
      <p class="mt-1 text-sm text-app-text-muted">{{ soloLectura ? 'Las canchas autorizadas aparecerán aquí.' : 'Registra una cancha para comenzar a organizar las instalaciones de tus sedes.' }}</p>
    </div>
    <div>
      <p v-if="canchas.length" class="text-sm text-app-text-muted" aria-live="polite">{{ total }} {{ total === 1 ? 'cancha registrada' : 'canchas registradas' }}</p>
      <div v-if="canchas.length" class="grid items-start gap-4 xl:grid-cols-2">
        <CanchaCard v-for="cancha in canchas" :key="cancha.id" :cancha="cancha" :sede-nombre="sedeNombrePorId.get(Number(cancha.sede_id || (typeof cancha.sede === 'object' ? cancha.sede?.id : ''))) || (typeof cancha.sede === 'string' ? cancha.sede : cancha.sede?.nombre) || ''" :solo-lectura="soloLectura" :subiendo-imagen="subiendoImagenId === cancha.id" :retirando-imagen-id="retirandoImagenId" @editar="editarCancha" @estado="cambiarEstado" @subir-imagen="subirImagen" @retirar-imagen="retirarImagen" />
      </div>
      <nav v-if="paginas > 1" class="flex flex-wrap items-center justify-between gap-3" aria-label="Paginación de canchas">
        <button class="admin-button admin-button-secondary" type="button" :disabled="cargando || pagina <= 1" @click="cargar(pagina - 1)"><ChevronLeft aria-hidden="true" class="size-4" />Anterior</button>
        <span class="text-sm text-app-text-muted">Página {{ pagina }} de {{ paginas }}</span>
        <button class="admin-button admin-button-secondary" type="button" :disabled="cargando || pagina >= paginas" @click="cargar(pagina + 1)">Siguiente<ChevronRight aria-hidden="true" class="size-4" /></button>
      </nav>
    </div>
  </section>
</template>
