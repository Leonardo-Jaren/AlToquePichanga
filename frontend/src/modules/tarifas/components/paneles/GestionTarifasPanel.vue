<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { Plus } from 'lucide-vue-next'
import { canchasApi } from '@/modules/canchas/services/canchas'
import SelectControl from '@/shared/components/controles/SelectControl.vue'
import { horariosApi } from '@/modules/horarios/services/horarios'
import { tarifasApi } from '../../services/tarifas'
import { mensajeErrorApi } from '../../utils/tarifas'
import TarifaForm from '../formularios/TarifaForm.vue'
import ReglasTarifa from '../listados/ReglasTarifa.vue'
import DisponibilidadTarifada from '../precios/DisponibilidadTarifada.vue'

const props = defineProps({
  sedes: { type: Array, default: () => [] },
  sedeInicialId: { type: [String, Number], default: '' },
  sedeFija: Boolean,
  soloLectura: Boolean,
  cargarSedes: Boolean,
})

const sedesInternas = ref([])
const sedeId = ref('')
const canchas = ref([])
const canchaId = ref('')
const reglas = ref([])
const tab = ref('reglas')
const cargando = ref(false)
const cargandoReglas = ref(false)
const guardando = ref(false)
const formulario = ref(false)
const tarifaEditando = ref(null)
const error = ref('')
const errorFormulario = ref('')
const mensaje = ref('')
const sedesVisibles = computed(() => props.cargarSedes ? sedesInternas.value : props.sedes)
const sedeSeleccionada = computed(() => sedesVisibles.value.find((sede) => String(sede.id) === sedeId.value))
const canchaSeleccionada = computed(() => canchas.value.find((cancha) => String(cancha.id) === canchaId.value))
let solicitudSede = 0
let solicitudReglas = 0

onMounted(iniciar)
watch(() => props.sedeInicialId, (id) => { if (id) seleccionarSede(id) })
watch(() => props.sedes.map((sede) => sede.id).join(','), () => {
  if (!props.cargarSedes && !props.sedeFija && !sedesVisibles.value.some((sede) => String(sede.id) === sedeId.value)) {
    sedeId.value = String(sedesVisibles.value[0]?.id || '')
    cargarSede()
  }
})

async function iniciar() {
  if (props.soloLectura) tab.value = 'precios'
  if (props.cargarSedes) {
    try {
      const { data } = await canchasApi.listarSedes()
      sedesInternas.value = normalizarLista(data)
    } catch (fallo) {
      error.value = mensajeErrorApi(fallo, 'No se pudieron cargar las sedes autorizadas.')
      return
    }
  }
  sedeId.value = String(props.sedeInicialId || sedesVisibles.value[0]?.id || '')
  await cargarSede()
}

function normalizarLista(data) { return Array.isArray(data) ? data : (data?.results || []) }

async function seleccionarSede(id) {
  if (String(id) === sedeId.value) return
  sedeId.value = String(id)
  await cargarSede()
}

async function cargarSede() {
  const solicitud = ++solicitudSede
  canchas.value = []
  canchaId.value = ''
  reglas.value = []
  error.value = ''
  mensaje.value = ''
  formulario.value = false
  if (!sedeId.value) return
  cargando.value = true
  try {
    const { data } = await horariosApi.listarCanchas(sedeId.value)
    if (solicitud !== solicitudSede) return
    canchas.value = normalizarLista(data)
    canchaId.value = String(canchas.value[0]?.id || '')
    if (canchaId.value) await cargarReglas()
  } catch (fallo) {
    if (solicitud === solicitudSede) error.value = mensajeErrorApi(fallo, 'No se pudieron cargar las canchas de esta sede.')
  } finally { if (solicitud === solicitudSede) cargando.value = false }
}

async function cambiarCancha() {
  error.value = ''
  mensaje.value = ''
  formulario.value = false
  await cargarReglas()
}

async function cargarReglas() {
  const solicitud = ++solicitudReglas
  reglas.value = []
  if (!canchaId.value) return
  cargandoReglas.value = true
  try {
    const { data } = await tarifasApi.listar(canchaId.value)
    if (solicitud === solicitudReglas) reglas.value = data.resultados || []
  } catch (fallo) {
    if (solicitud === solicitudReglas) error.value = mensajeErrorApi(fallo, 'No se pudieron cargar las tarifas de esta cancha.')
  } finally { if (solicitud === solicitudReglas) cargandoReglas.value = false }
}

function nuevaTarifa() {
  errorFormulario.value = ''
  tarifaEditando.value = null
  formulario.value = true
}

function editarTarifa(tarifa) {
  errorFormulario.value = ''
  tarifaEditando.value = { ...tarifa }
  formulario.value = true
}

async function guardarTarifa(datos) {
  guardando.value = true
  errorFormulario.value = ''
  try {
    if (tarifaEditando.value) await tarifasApi.actualizar(canchaId.value, tarifaEditando.value.id, datos)
    else await tarifasApi.crear(canchaId.value, datos)
    formulario.value = false
    mensaje.value = tarifaEditando.value ? 'Tarifa actualizada.' : 'Tarifa creada.'
    tarifaEditando.value = null
    await cargarReglas()
  } catch (fallo) {
    errorFormulario.value = mensajeErrorApi(fallo, 'No se pudo guardar la tarifa. Revisa los datos e inténtalo otra vez.')
  } finally { guardando.value = false }
}

async function cambiarEstado(tarifa) {
  const accion = tarifa.activa ? 'desactivar' : 'activar'
  const pregunta = tarifa.activa
    ? `¿Desactivar “${tarifa.nombre || tarifa.tipo}”? Se conservará en el historial.`
    : `¿Activar “${tarifa.nombre || tarifa.tipo}”? El sistema validará que no se cruce con otra regla.`
  if (!window.confirm(pregunta)) return
  error.value = ''
  mensaje.value = ''
  try {
    await tarifasApi.cambiarEstado(canchaId.value, tarifa.id, !tarifa.activa)
    mensaje.value = `Tarifa ${accion === 'desactivar' ? 'desactivada' : 'activada'}.`
    await cargarReglas()
  } catch (fallo) {
    error.value = mensajeErrorApi(fallo, 'No se pudo cambiar el estado de la tarifa.')
  }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="gestion-tarifas-titulo">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div><h2 id="gestion-tarifas-titulo" class="font-display text-xl">Tarifas por cancha</h2><p class="mt-1 max-w-2xl text-sm text-app-text-muted">Configura precios por día, horario y fechas especiales. Cada cancha mantiene sus propias reglas.</p></div>
      <SelectControl v-if="!sedeFija && sedesVisibles.length" id="tarifas-sede" :model-value="sedeId" label="Sede" :options="sedesVisibles.map((sede) => ({ value: String(sede.id), label: sede.nombre }))" placeholder="Selecciona una sede" @update:model-value="seleccionarSede" />
      <p v-else-if="sedeSeleccionada" class="rounded-lg border border-app-border bg-app-surface-2 px-3 py-2 text-sm font-semibold">{{ sedeSeleccionada.nombre }}</p>
    </div>
    <div v-if="sedeId && canchas.length" class="max-w-xl">
      <SelectControl id="tarifas-cancha" v-model="canchaId" label="Cancha" :options="canchas.map((cancha) => ({ value: String(cancha.id), label: cancha.nombre }))" placeholder="Selecciona una cancha" @update:model-value="cambiarCancha" />
    </div>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>
    <p v-if="cargando" role="status" class="admin-card">Cargando sedes y canchas…</p>
    <div v-else-if="!sedesVisibles.length" class="admin-card"><h3 class="font-bold">No hay sedes para consultar</h3><p class="mt-1 text-sm text-app-text-muted">Las sedes autorizadas aparecerán aquí.</p></div>
    <div v-else-if="!canchas.length" class="admin-card"><h3 class="font-bold">Esta sede aún no tiene canchas</h3><p class="mt-1 text-sm text-app-text-muted">Primero agrega una cancha para configurar o consultar sus precios.</p></div>
    <template v-else-if="canchaId">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div><p class="text-sm text-app-text-muted">{{ sedeSeleccionada?.nombre }}</p><h3 class="text-lg font-bold">{{ canchaSeleccionada?.nombre }}</h3></div>
        <button v-if="!soloLectura && tab === 'reglas' && !formulario" class="admin-button admin-button-primary" type="button" @click="nuevaTarifa"><Plus aria-hidden="true" class="size-4" />Agregar tarifa</button>
      </div>
      <nav class="flex flex-wrap gap-2" aria-label="Secciones de tarifas">
        <button class="admin-button" :class="tab === 'reglas' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="tab === 'reglas'" @click="tab = 'reglas'">Reglas</button>
        <button class="admin-button" :class="tab === 'precios' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="tab === 'precios'" @click="tab = 'precios'">Precios por horario</button>
      </nav>
      <p v-if="cargandoReglas" role="status" class="admin-card">Cargando reglas de esta cancha…</p>
      <TarifaForm v-else-if="tab === 'reglas' && formulario" :key="tarifaEditando?.id || 'nueva-tarifa'" :tarifa="tarifaEditando" :guardando="guardando" :error="errorFormulario" @guardar="guardarTarifa" @cancelar="formulario = false" />
      <ReglasTarifa v-else-if="tab === 'reglas'" :reglas="reglas" :solo-lectura="soloLectura" @editar="editarTarifa" @cambiar-estado="cambiarEstado" />
      <DisponibilidadTarifada v-else :key="'precios-' + canchaId" :cancha-id="canchaId" />
    </template>
  </section>
</template>
