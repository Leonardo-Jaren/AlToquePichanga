<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { CalendarClock, CalendarDays, Clock3 } from 'lucide-vue-next'
import { canchasApi } from '@/modules/canchas/services/canchas'
import { horariosApi } from '../services/horarios'
import { normalizarIntervalos, validarIntervalos, validarIntervalosDentroDeMarco } from '../utils/horarios'
import SemanaEditor from './SemanaEditor.vue'
import ExcepcionesPanel from './ExcepcionesPanel.vue'
import DisponibilidadOperativa from './DisponibilidadOperativa.vue'

const props = defineProps({
  sedes: { type: Array, default: () => [] },
  sedeInicialId: { type: [Number, String], default: '' },
  sedeFija: { type: Boolean, default: false },
  soloLectura: { type: Boolean, default: false },
  cargarSedes: { type: Boolean, default: false },
})

const sedesInternas = ref([])
const sedeId = ref('')
const canchas = ref([])
const canchaId = ref('')
const tab = ref('semana')
const horarioSede = ref([])
const horarioCancha = ref([])
const diasHeredados = ref([0, 1, 2, 3, 4, 5, 6])
const cargando = ref(false)
const cargandoCancha = ref(false)
const guardandoSede = ref(false)
const guardandoCancha = ref(false)
const error = ref('')
const mensaje = ref('')
const hayHorarioSede = ref(false)
const hayHorarioCancha = ref(false)
const listaSedes = computed(() => props.cargarSedes ? sedesInternas.value : props.sedes)
const sedeSeleccionada = computed(() => listaSedes.value.find((sede) => String(sede.id) === String(sedeId.value)))
const canchaSeleccionada = computed(() => canchas.value.find((cancha) => String(cancha.id) === String(canchaId.value)))
const heredaCompleto = computed(() => diasHeredados.value.length === 7)
const guardarSedeBloqueado = computed(() => Boolean(validarIntervalos(horarioSede.value)))
const guardarCanchaBloqueado = computed(() => !heredaCompleto.value && Boolean(validarIntervalos(horarioCancha.value)))
const diasErrorSede = computed(() => validarIntervalos(horarioSede.value))
const diasErrorCancha = computed(() => validarIntervalos(horarioCancha.value) || validarIntervalosDentroDeMarco(horarioCancha.value, horarioSede.value))
const secciones = [
  { id: 'semana', nombre: 'Semana', icono: CalendarClock },
  { id: 'excepciones', nombre: 'Cierres y cambios', icono: Clock3 },
  { id: 'operativo', nombre: 'Horario operativo', icono: CalendarDays },
]
let solicitudSede = 0
let solicitudCancha = 0

onMounted(iniciar)
watch(() => props.sedeInicialId, (id) => { if (id) seleccionarSede(id) })
watch(() => props.sedes.map((sede) => sede.id).join(','), () => {
  if (!props.cargarSedes && !props.sedeFija && !listaSedes.value.some((sede) => String(sede.id) === String(sedeId.value))) {
    sedeId.value = listaSedes.value[0]?.id ? String(listaSedes.value[0].id) : ''
    cargarSede()
  }
})

async function iniciar() {
  if (props.cargarSedes) {
    try { sedesInternas.value = normalizarLista((await canchasApi.listarSedes()).data) }
    catch (fallo) { error.value = fallo.response?.data?.detail || 'No se pudieron cargar las sedes autorizadas.'; return }
  }
  const inicial = props.sedeInicialId || listaSedes.value[0]?.id
  sedeId.value = inicial ? String(inicial) : ''
  await cargarSede()
}

function normalizarLista(data) { return Array.isArray(data) ? data : data?.results || [] }
async function seleccionarSede(id) {
  if (String(id) === String(sedeId.value)) return
  sedeId.value = String(id)
  await cargarSede()
}
async function cargarSede() {
  const actual = ++solicitudSede
  if (!sedeId.value) { canchas.value = []; canchaId.value = ''; return }
  cargando.value = true
  error.value = ''
  mensaje.value = ''
  try {
    const [respuestaHorario, respuestaCanchas] = await Promise.all([
      horariosApi.horarioSede(sedeId.value), horariosApi.listarCanchas(sedeId.value),
    ])
    if (actual !== solicitudSede) return
    horarioSede.value = normalizarIntervalos(respuestaHorario.data.intervalos || [])
    hayHorarioSede.value = Boolean(respuestaHorario.data.configurado)
    canchas.value = normalizarLista(respuestaCanchas.data)
    canchaId.value = canchas.value.some((item) => String(item.id) === String(canchaId.value))
      ? String(canchaId.value) : (canchas.value[0]?.id ? String(canchas.value[0].id) : '')
    await cargarHorarioCancha()
  } catch (fallo) {
    if (actual !== solicitudSede) return
    error.value = fallo.response?.data?.detail || 'No se pudieron cargar los horarios de la sede.'
    horarioSede.value = []
    canchas.value = []
  } finally { if (actual === solicitudSede) cargando.value = false }
}

async function cargarHorarioCancha() {
  const actual = ++solicitudCancha
  if (!canchaId.value) { horarioCancha.value = []; hayHorarioCancha.value = false; return }
  cargandoCancha.value = true
  try {
    const { data } = await horariosApi.horarioCancha(canchaId.value)
    if (actual !== solicitudCancha) return
    diasHeredados.value = data.hereda_horario_sede ? [0, 1, 2, 3, 4, 5, 6] : (data.dias_heredados || []).map(Number)
    horarioCancha.value = normalizarIntervalos(data.intervalos || [])
    hayHorarioCancha.value = Boolean(data.configurado)
  } catch (fallo) {
    if (actual !== solicitudCancha) return
    error.value = fallo.response?.data?.detail || 'No se pudo cargar el horario de la cancha.'
    horarioCancha.value = []
  } finally { if (actual === solicitudCancha) cargandoCancha.value = false }
}
async function seleccionarCancha() { error.value = ''; mensaje.value = ''; await cargarHorarioCancha() }
async function guardarHorarioSede() {
  error.value = ''
  mensaje.value = ''
  if (diasErrorSede.value) { error.value = diasErrorSede.value; return }
  guardandoSede.value = true
  try {
    const { data } = await horariosApi.guardarHorarioSede(sedeId.value, { intervalos: normalizarIntervalos(horarioSede.value) })
    horarioSede.value = normalizarIntervalos(data.intervalos || horarioSede.value)
    hayHorarioSede.value = Boolean(data.configurado ?? true)
    mensaje.value = 'Horario semanal de la sede guardado.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat().join(' ') || 'No se pudo guardar el horario de la sede.'
  } finally { guardandoSede.value = false }
}
function cambiarHerencia(dia) {
  if (diasHeredados.value.includes(dia)) {
    diasHeredados.value = diasHeredados.value.filter((item) => item !== dia)
    const copiaSede = horarioSede.value.filter((item) => item.dia_semana === dia)
    const propios = horarioCancha.value.filter((item) => item.dia_semana !== dia)
    horarioCancha.value = normalizarIntervalos([...propios, ...copiaSede])
  } else {
    diasHeredados.value = [...diasHeredados.value, dia].sort((a, b) => a - b)
    horarioCancha.value = horarioCancha.value.filter((item) => item.dia_semana !== dia)
  }
}
async function guardarHorarioCancha() {
  error.value = ''
  mensaje.value = ''
  if (guardarCanchaBloqueado.value) { error.value = diasErrorCancha.value; return }
  guardandoCancha.value = true
  try {
    const todosHeredados = diasHeredados.value.length === 7
    const datos = {
      hereda_horario_sede: todosHeredados,
      dias_heredados: todosHeredados ? [] : [...diasHeredados.value].sort((a, b) => a - b),
      intervalos: todosHeredados ? [] : normalizarIntervalos(horarioCancha.value),
    }
    const { data } = await horariosApi.guardarHorarioCancha(canchaId.value, datos)
    diasHeredados.value = data.hereda_horario_sede ? [0, 1, 2, 3, 4, 5, 6] : (data.dias_heredados || []).map(Number)
    horarioCancha.value = normalizarIntervalos(data.intervalos || [])
    hayHorarioCancha.value = Boolean(data.configurado)
    mensaje.value = 'Horario de la cancha guardado.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat().join(' ') || 'No se pudo guardar el horario de la cancha.'
  } finally { guardandoCancha.value = false }
}
function actualizarSede(intervalos) { horarioSede.value = intervalos }
function actualizarCancha(intervalos) { horarioCancha.value = intervalos }
</script>

<template>
  <section class="space-y-5" aria-labelledby="gestion-horarios-titulo">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div><h2 id="gestion-horarios-titulo" class="text-xl font-bold">Horarios y cierres</h2><p class="mt-1 text-sm text-app-text-muted">Organiza los días y horas operativas de cada sede y cancha.</p></div>
      <label v-if="!sedeFija && listaSedes.length" class="min-w-56 flex-1 sm:max-w-xs"><span class="admin-label">Sede</span><select v-model="sedeId" class="admin-field" aria-label="Seleccionar sede" @change="cargarSede"><option v-for="sede in listaSedes" :key="sede.id" :value="String(sede.id)">{{ sede.nombre }}</option></select></label>
      <p v-else-if="sedeSeleccionada" class="rounded-lg border border-app-border bg-app-surface-2 px-3 py-2 text-sm font-semibold">{{ sedeSeleccionada.nombre }}</p>
    </div>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="mensaje" class="admin-success" role="status">{{ mensaje }}</p>
    <p v-if="cargando" class="admin-card" role="status">Cargando horarios de la sede…</p>
    <div v-else-if="!listaSedes.length" class="admin-card"><h3 class="font-bold">No hay sedes para consultar</h3><p class="mt-1 text-sm text-app-text-muted">Las sedes autorizadas aparecerán aquí.</p></div>
    <template v-else>
      <nav class="flex flex-wrap gap-2" aria-label="Secciones de horarios">
        <button v-for="item in secciones" :key="item.id" class="admin-button" :class="tab === item.id ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="tab === item.id" @click="tab = item.id"><component :is="item.icono" aria-hidden="true" class="size-4" />{{ item.nombre }}</button>
      </nav>
      <section v-if="tab === 'semana'" class="space-y-6" aria-label="Horarios semanales">
        <article class="admin-card space-y-4 border-t-2 border-t-brand-lime">
          <SemanaEditor titulo="Semana de la sede" descripcion="Este horario marca el marco operativo del complejo." :intervalos="horarioSede" :editable="!soloLectura" @actualizar="actualizarSede" />
          <p v-if="!hayHorarioSede" class="text-sm text-app-text-muted">Aún no hay un horario semanal guardado.</p>
          <p v-if="diasErrorSede" class="admin-error" role="alert">{{ diasErrorSede }}</p>
          <button v-if="!soloLectura" class="admin-button admin-button-primary" type="button" :disabled="guardandoSede || guardarSedeBloqueado" @click="guardarHorarioSede">{{ guardandoSede ? 'Guardando…' : 'Guardar horario de sede' }}</button>
        </article>
        <article class="admin-card space-y-4">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div><h3 class="text-lg font-bold">Horario por cancha</h3><p class="mt-1 text-sm text-app-text-muted">El carril lima muestra el horario propio dentro del marco de la sede.</p></div>
            <label v-if="canchas.length" class="min-w-56 flex-1 sm:max-w-xs"><span class="admin-label">Cancha</span><select v-model="canchaId" class="admin-field" aria-label="Seleccionar cancha" @change="seleccionarCancha"><option v-for="cancha in canchas" :key="cancha.id" :value="String(cancha.id)">{{ cancha.nombre }}</option></select></label>
          </div>
          <p v-if="!canchas.length" class="rounded-xl bg-app-surface-2 p-4 text-sm text-app-text-muted">Esta sede todavía no tiene canchas para configurar.</p>
          <template v-else>
            <p v-if="cargandoCancha" role="status" class="text-sm text-app-text-muted">Cargando horario de {{ canchaSeleccionada?.nombre }}…</p>
            <div v-else class="space-y-4">
              <p class="rounded-lg border border-app-border bg-app-surface-2 p-3 text-sm text-app-text-muted">Cada día puede heredar el horario de sede, tener horas propias o quedar cerrado. Las horas propias deben respetar el marco operativo de la sede.</p>
              <SemanaEditor titulo="Semana de la cancha" descripcion="Elige por día si hereda de sede o usa su carril lima propio." :intervalos="horarioCancha" :marco-intervalos="horarioSede" :dias-heredados="diasHeredados" :permite-herencia="true" :editable="!soloLectura" @actualizar="actualizarCancha" @heredar-dia="cambiarHerencia" />
              <p v-if="!hayHorarioCancha && !heredaCompleto" class="text-sm text-app-text-muted">Aún no hay un horario propio guardado.</p>
              <p v-if="!heredaCompleto && diasErrorCancha" class="admin-error" role="alert">{{ diasErrorCancha }}</p>
              <button v-if="!soloLectura" class="admin-button admin-button-primary" type="button" :disabled="guardandoCancha || guardarCanchaBloqueado || !canchaId" @click="guardarHorarioCancha">{{ guardandoCancha ? 'Guardando…' : 'Guardar horario de cancha' }}</button>
            </div>
          </template>
        </article>
      </section>
      <ExcepcionesPanel v-else-if="tab === 'excepciones' && sedeId" :key="`excepciones-${sedeId}`" :sede-id="sedeId" :canchas="canchas" :solo-lectura="soloLectura" />
      <DisponibilidadOperativa v-else-if="tab === 'operativo'" :cancha-id="canchaId" :solo-lectura="soloLectura" />
    </template>
  </section>
</template>
