<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { CalendarClock, CircleOff, Plus } from 'lucide-vue-next'
import { horariosApi } from '../services/horarios'
import { fechaHoraLima } from '../utils/horarios'

const props = defineProps({ sedeId: { type: [Number, String], required: true }, canchas: { type: Array, default: () => [] }, soloLectura: { type: Boolean, default: false } })
const emit = defineEmits(['cambio'])
const excepciones = ref([])
const cargando = ref(false)
const guardando = ref(false)
const anulando = ref(null)
const error = ref('')
const mensaje = ref('')
const formularioAbierto = ref(false)
const hoy = fechaActualLima()
const formulario = reactive({ cancha_id: '', tipo: 'cierre', fecha_inicio: hoy, hora_inicio: '08:00', fecha_fin: hoy, hora_fin: '22:00', motivo: '' })
const proxima = computed(() => excepciones.value
  .filter((item) => !item.anulada && Date.parse(item.fecha_fin) >= Date.now())
  .sort((a, b) => Date.parse(a.fecha_inicio) - Date.parse(b.fecha_inicio)))

onMounted(cargar)
watch(() => props.sedeId, cargar)

function fechaActualLima() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
}
function fechaTexto(valor) {
  if (!valor) return ''
  return new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', dateStyle: 'medium', timeStyle: 'short' }).format(new Date(valor))
}
async function cargar() {
  if (!props.sedeId) return
  cargando.value = true
  error.value = ''
  try {
    const { data } = await horariosApi.listarExcepciones({ sede: props.sedeId, desde: hoy })
    excepciones.value = Array.isArray(data) ? data : data.results || []
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudieron cargar los cierres y cambios de horario.'
  } finally { cargando.value = false }
}
function abrirFormulario() {
  Object.assign(formulario, { cancha_id: '', tipo: 'cierre', fecha_inicio: hoy, hora_inicio: '08:00', fecha_fin: hoy, hora_fin: '22:00', motivo: '' })
  formularioAbierto.value = true
  error.value = ''
}
async function guardar() {
  error.value = ''
  mensaje.value = ''
  if (formulario.fecha_fin < formulario.fecha_inicio || (formulario.fecha_fin === formulario.fecha_inicio && formulario.hora_fin <= formulario.hora_inicio)) {
    error.value = 'El final debe ocurrir después del inicio.'
    return
  }
  if (!formulario.motivo.trim()) { error.value = 'Escribe el motivo del cambio.'; return }
  guardando.value = true
  const datos = {
    sede_id: Number(props.sedeId),
    tipo: formulario.tipo,
    fecha_inicio: fechaHoraLima(formulario.fecha_inicio, formulario.hora_inicio),
    fecha_fin: fechaHoraLima(formulario.fecha_fin, formulario.hora_fin),
    motivo: formulario.motivo.trim(),
  }
  if (formulario.cancha_id) datos.cancha_id = Number(formulario.cancha_id)
  try {
    await horariosApi.crearExcepcion(datos)
    formularioAbierto.value = false
    mensaje.value = formulario.tipo === 'cierre' ? 'Cierre registrado.' : 'Ampliación registrada.'
    await cargar()
    emit('cambio')
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat().join(' ') || 'No se pudo registrar el cambio.'
  } finally { guardando.value = false }
}
async function anular(item) {
  if (!window.confirm('¿Anular este cambio de horario? El registro quedará en el historial.')) return
  error.value = ''
  anulando.value = item.id
  try {
    await horariosApi.anularExcepcion(item.id)
    mensaje.value = 'Cambio anulado; el historial se conservó.'
    await cargar()
    emit('cambio')
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo anular el cambio.'
  } finally { anulando.value = null }
}
</script>

<template>
  <section class="space-y-4" aria-labelledby="excepciones-titulo">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div><h3 id="excepciones-titulo" class="text-lg font-bold">Cierres y cambios de horario</h3><p class="mt-1 text-sm text-app-text-muted">Los cierres de sede alcanzan sus canchas. Las ampliaciones no anulan cierres vigentes.</p></div>
      <button v-if="!soloLectura" class="admin-button admin-button-primary" type="button" @click="abrirFormulario"><Plus aria-hidden="true" class="size-4" />Registrar excepción</button>
    </div>
    <p class="rounded-xl border border-app-border bg-app-surface-2 p-3 text-sm text-app-text-muted">Zona horaria: America/Lima (UTC−05:00). El horario operativo no consulta reservas.</p>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="mensaje" class="admin-success" role="status">{{ mensaje }}</p>
    <form v-if="formularioAbierto" class="admin-card grid gap-4 sm:grid-cols-2" novalidate :aria-busy="guardando" @submit.prevent="guardar">
      <h4 class="font-bold sm:col-span-2">Nueva excepción</h4>
      <label><span class="admin-label">Afecta a</span><select v-model="formulario.cancha_id" class="admin-field"><option value="">Toda la sede</option><option v-for="cancha in canchas" :key="cancha.id" :value="String(cancha.id)">{{ cancha.nombre }}</option></select></label>
      <label><span class="admin-label">Tipo</span><select v-model="formulario.tipo" class="admin-field"><option value="cierre">Cierre</option><option value="ampliacion">Ampliación de horario</option></select></label>
      <label><span class="admin-label">Fecha de inicio</span><input v-model="formulario.fecha_inicio" class="admin-field" type="date" required></label>
      <label><span class="admin-label">Hora de inicio (Perú)</span><input v-model="formulario.hora_inicio" class="admin-field" type="time" required></label>
      <label><span class="admin-label">Fecha de fin</span><input v-model="formulario.fecha_fin" class="admin-field" type="date" required></label>
      <label><span class="admin-label">Hora de fin (Perú)</span><input v-model="formulario.hora_fin" class="admin-field" type="time" required></label>
      <label class="sm:col-span-2"><span class="admin-label">Motivo</span><input v-model.trim="formulario.motivo" class="admin-field" maxlength="240" required placeholder="Mantenimiento, feriado, evento privado…"></label>
      <div class="flex flex-wrap gap-2 sm:col-span-2"><button class="admin-button admin-button-primary" :disabled="guardando">{{ guardando ? 'Guardando…' : 'Guardar excepción' }}</button><button class="admin-button admin-button-secondary" type="button" :disabled="guardando" @click="formularioAbierto = false">Cancelar</button></div>
    </form>
    <p v-if="cargando" role="status" class="admin-card">Cargando próximos cierres…</p>
    <div v-else-if="!proxima.length" class="admin-card border-l-2 border-l-brand-lime">
      <CalendarClock aria-hidden="true" class="mb-2 size-5 text-app-text-muted"/><h4 class="font-bold">Sin excepciones próximas</h4><p class="mt-1 text-sm text-app-text-muted">Los horarios semanales seguirán aplicándose.</p>
    </div>
    <ul v-else class="grid gap-3 lg:grid-cols-2">
      <li v-for="item in proxima" :key="item.id" class="admin-card flex flex-wrap items-start justify-between gap-3 border-l-2" :class="item.tipo === 'cierre' ? 'border-l-[var(--status-danger-text)]' : 'border-l-brand-lime'">
        <div class="min-w-0"><div class="flex flex-wrap items-center gap-2"><CircleOff v-if="item.tipo === 'cierre'" aria-hidden="true" class="size-4 text-[var(--status-danger-text)]"/><span class="font-bold">{{ item.tipo === 'cierre' ? 'Cierre' : 'Ampliación de horario' }}</span><span v-if="item.anulada" class="admin-state admin-state-info">Anulada</span></div><p class="mt-2 text-sm tabular-nums">{{ fechaTexto(item.fecha_inicio) }} – {{ fechaTexto(item.fecha_fin) }}</p><p class="mt-1 text-sm text-app-text-muted">{{ item.cancha_id ? (canchas.find((cancha) => Number(cancha.id) === Number(item.cancha_id))?.nombre || 'Cancha') : 'Toda la sede' }} · {{ item.motivo }}</p></div>
        <button v-if="!soloLectura && !item.anulada" class="admin-button admin-button-secondary" type="button" :disabled="anulando === item.id" @click="anular(item)">{{ anulando === item.id ? 'Anulando…' : 'Anular' }}</button>
      </li>
    </ul>
  </section>
</template>
