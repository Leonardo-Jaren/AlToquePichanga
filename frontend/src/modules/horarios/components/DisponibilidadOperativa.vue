<script setup>
import { computed, ref, watch } from 'vue'
import { CalendarDays, RefreshCw } from 'lucide-vue-next'
import { horariosApi } from '../services/horarios'
import { diasEntre } from '../utils/horarios'

const props = defineProps({ canchaId: { type: [Number, String], default: '' }, soloLectura: { type: Boolean, default: false } })
const fechaBase = fechaActualLima()
const desde = ref(fechaBase)
const hasta = ref(desplazar(fechaBase, 6))
const cargando = ref(false)
const error = ref('')
const bloques = ref([])
const consultaRealizada = ref(false)
const rangoValido = computed(() => diasEntre(desde.value, hasta.value) >= 0 && diasEntre(desde.value, hasta.value) <= 30)
const agrupados = computed(() => {
  const grupos = new Map()
  for (const bloque of bloques.value) {
    const fecha = bloque.fecha_inicio?.slice(0, 10) || ''
    if (!grupos.has(fecha)) grupos.set(fecha, [])
    grupos.get(fecha).push(bloque)
  }
  return [...grupos.entries()].map(([fecha, items]) => ({ fecha, rotulo: fechaEtiqueta(fecha), bloques: items }))
})

watch(() => props.canchaId, () => { bloques.value = []; consultaRealizada.value = false })

function fechaActualLima() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date())
}
function desplazar(fecha, dias) {
  const base = new Date(`${fecha}T12:00:00Z`)
  base.setUTCDate(base.getUTCDate() + dias)
  return base.toISOString().slice(0, 10)
}
function fechaEtiqueta(fecha) {
  const [year, month, day] = fecha.split('-').map(Number)
  return new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', weekday: 'long', day: 'numeric', month: 'long' }).format(new Date(Date.UTC(year, month - 1, day, 12)))
}
function hora(valor) {
  return new Intl.DateTimeFormat('es-PE', { timeZone: 'America/Lima', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(valor))
}
function etiquetaEstado(bloque) {
  if (bloque.estado === 'operativa' || bloque.habilitada_operativamente) return 'Dentro del horario operativo'
  return ({ cerrada: 'Cerrado', pasada: 'Horario pasado', sede_inactiva: 'Sede inactiva', cancha_inactiva: 'Cancha inactiva', mantenimiento: 'En mantenimiento' })[bloque.estado] || 'Fuera del horario operativo'
}
function estiloEstado(bloque) {
  return bloque.estado === 'operativa' || bloque.habilitada_operativamente
    ? 'bg-[var(--status-success-bg)] text-[var(--status-success-text)]'
    : 'bg-app-surface-2 text-app-text-muted'
}
async function consultar() {
  if (!props.canchaId || !rangoValido.value) return
  error.value = ''
  cargando.value = true
  consultaRealizada.value = true
  try {
    const { data } = await horariosApi.disponibilidad(props.canchaId, desde.value, hasta.value)
    bloques.value = Array.isArray(data.bloques) ? data.bloques : []
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo consultar el horario operativo.'
    bloques.value = []
  } finally { cargando.value = false }
}
</script>

<template>
  <section class="space-y-4" aria-labelledby="disponibilidad-titulo">
    <div><h3 id="disponibilidad-titulo" class="text-lg font-bold">Horario operativo</h3><p class="mt-1 text-sm text-app-text-muted">Consulta los bloques de 60 minutos definidos por los horarios y excepciones.</p></div>
    <p class="rounded-xl border border-app-border bg-app-surface-2 p-3 text-sm font-medium">Horario operativo solamente. No consulta reservas y no indica que un bloque esté libre para reservar.</p>
    <form class="admin-card grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end" @submit.prevent="consultar">
      <label><span class="admin-label">Desde (Perú)</span><input v-model="desde" class="admin-field" type="date" required></label>
      <label><span class="admin-label">Hasta (Perú)</span><input v-model="hasta" class="admin-field" type="date" required></label>
      <button class="admin-button admin-button-primary" type="submit" :disabled="cargando || !canchaId || !rangoValido"><RefreshCw aria-hidden="true" class="size-4" />{{ cargando ? 'Consultando…' : 'Consultar horario' }}</button>
      <p v-if="!canchaId" class="text-sm text-app-text-muted sm:col-span-3">Selecciona una cancha para consultar su horario.</p>
      <p v-if="!rangoValido" class="text-sm text-[var(--status-danger-text)] sm:col-span-3" role="alert">El rango debe ser válido y abarcar como máximo 31 días (incluidos).</p>
    </form>
    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="cargando" class="admin-card" role="status">Calculando bloques operativos…</p>
    <div v-else-if="consultaRealizada && !error && !bloques.length" class="admin-card"><CalendarDays aria-hidden="true" class="mb-2 size-5 text-app-text-muted"/><p class="font-semibold">No hay bloques operativos en este rango.</p></div>
    <div v-else-if="bloques.length" class="space-y-4">
      <section v-for="grupo in agrupados" :key="grupo.fecha" class="admin-card" :aria-label="grupo.rotulo">
        <h4 class="mb-3 font-bold capitalize">{{ grupo.rotulo }}</h4>
        <ul class="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
          <li v-for="(bloque, indice) in grupo.bloques" :key="`${grupo.fecha}-${indice}`" class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-app-border px-3 py-2.5">
            <span class="font-semibold tabular-nums">{{ hora(bloque.fecha_inicio) }}–{{ hora(bloque.fecha_fin) }}</span>
            <span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="estiloEstado(bloque)">{{ etiquetaEstado(bloque) }}</span>
            <span v-if="bloque.motivo" class="w-full text-xs text-app-text-muted">{{ bloque.motivo }}</span>
          </li>
        </ul>
      </section>
    </div>
  </section>
</template>
