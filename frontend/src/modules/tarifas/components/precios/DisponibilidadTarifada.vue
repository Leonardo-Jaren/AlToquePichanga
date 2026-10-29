<script setup>
import { computed, ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import SelectControl from '@/shared/components/controles/SelectControl.vue'
import { horariosApi } from '@/modules/horarios/services/horarios'
import { tarifasApi } from '../../services/tarifas'
import { desplazarFecha, fechaActualLima, fechaEtiqueta, formatearPEN, horaEtiqueta, mensajeErrorApi } from '../../utils/tarifas'

const props = defineProps({ canchaId: { type: [Number, String], default: '' } })
const fecha = ref(fechaActualLima())
const bloques = ref([])
const cargando = ref(false)
const calculando = ref(false)
const error = ref('')
const resultado = ref(null)
const horaInicio = ref('')
const duracion = ref('1')
const consultado = ref(false)
const horasDisponibles = computed(() => bloques.value
  .filter((bloque) => bloque.habilitada_operativamente)
  .map((bloque) => ({ value: String(bloque.fecha_inicio).slice(11, 16), label: horaEtiqueta(bloque.fecha_inicio) })))
const duraciones = Array.from({ length: 24 }, (_, indice) => ({ value: String(indice + 1), label: `${indice + 1} ${indice ? 'horas' : 'hora'}` }))

watch(() => props.canchaId, () => { bloques.value = []; resultado.value = null; consultado.value = false })

async function consultar() {
  if (!props.canchaId || !fecha.value) return
  cargando.value = true
  error.value = ''
  resultado.value = null
  consultado.value = true
  try {
    const { data } = await horariosApi.disponibilidad(props.canchaId, fecha.value, fecha.value)
    bloques.value = Array.isArray(data.bloques) ? data.bloques : []
    horaInicio.value = horasDisponibles.value[0]?.value || ''
    if (data.considera_reservas !== false) error.value = 'La respuesta de disponibilidad no incluyó el indicador operativo esperado.'
  } catch (fallo) {
    error.value = mensajeErrorApi(fallo, 'No se pudieron consultar los precios de esta fecha.')
    bloques.value = []
  } finally { cargando.value = false }
}

async function calcular() {
  if (!horaInicio.value || !duracion.value) return
  calculando.value = true
  error.value = ''
  resultado.value = null
  try {
    resultado.value = (await tarifasApi.calcular(props.canchaId, {
      fecha: fecha.value, hora_inicio: horaInicio.value, duracion_horas: Number.parseInt(duracion.value, 10),
    })).data
  } catch (fallo) {
    error.value = mensajeErrorApi(fallo, 'No se pudo calcular el precio para esos bloques.')
  } finally { calculando.value = false }
}

function estado(bloque) {
  if (!bloque.habilitada_operativamente) return 'Cerrado · no se muestra precio'
  if (bloque.tarifa_estado === 'sin_configurar') return 'Habilitado · sin tarifa'
  return 'Habilitado'
}
</script>

<template>
  <section class="space-y-4" aria-labelledby="precios-horario-titulo">
    <div><h3 id="precios-horario-titulo" class="font-display text-lg">Precios por horario</h3><p class="mt-1 text-sm text-app-text-muted">Consulta los bloques operativos de una fecha y previsualiza el total desde la API.</p></div>
    <form class="admin-card grid items-end gap-3 sm:grid-cols-[minmax(180px,1fr)_auto]" @submit.prevent="consultar">
      <label><span class="admin-label">Fecha de consulta</span><input v-model="fecha" class="admin-field" type="date" required></label>
      <button class="admin-button admin-button-secondary" :disabled="cargando || !canchaId"><RefreshCw aria-hidden="true" class="size-4" />{{ cargando ? 'Consultando…' : 'Consultar precios' }}</button>
    </form>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="cargando" role="status" class="admin-card">Cargando bloques y precios…</p>
    <div v-else-if="consultado && !bloques.length" class="admin-card">
      <h4 class="font-bold">Sin bloques operativos para {{ fechaEtiqueta(fecha) }}</h4>
      <p class="mt-1 text-sm text-app-text-muted">Revisa los horarios semanales y las excepciones de la cancha.</p>
    </div>
    <section v-else-if="bloques.length" class="admin-card" aria-label="Bloques y precios">
      <div class="mb-3 flex flex-wrap items-center justify-between gap-2"><h4 class="font-bold">{{ fechaEtiqueta(fecha) }}</h4><span class="text-xs text-app-text-muted">Zona horaria: America/Lima</span></div>
      <div class="divide-y divide-app-border">
        <article v-for="bloque in bloques" :key="bloque.fecha_inicio" class="grid gap-2 py-3 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] sm:items-center">
          <p class="font-semibold tabular-nums">{{ horaEtiqueta(bloque.fecha_inicio) }}–{{ horaEtiqueta(bloque.fecha_fin) }}</p>
          <p class="text-sm" :class="bloque.habilitada_operativamente ? 'text-[var(--status-success-text)]' : 'text-app-text-muted'">{{ estado(bloque) }}<span v-if="bloque.motivo" class="block text-xs text-app-text-muted">{{ bloque.motivo }}</span></p>
          <strong v-if="bloque.habilitada_operativamente && bloque.tarifa_estado === 'configurada'" class="tabular-nums">{{ formatearPEN(bloque.precio, bloque.moneda) }}<span class="ml-1 text-xs font-normal text-app-text-muted">{{ bloque.tipo_tarifa }}</span></strong>
          <span v-else class="text-sm text-app-text-muted">—</span>
        </article>
      </div>
      <p class="mt-3 rounded-lg bg-app-surface-2 p-3 text-xs text-app-text-muted">Este indicador describe el horario operativo. No consulta reservas ni confirma que el bloque esté libre para alquilar.</p>
    </section>
    <form v-if="bloques.some((bloque) => bloque.habilitada_operativamente)" class="admin-card grid gap-4 sm:grid-cols-3" @submit.prevent="calcular">
      <div class="sm:col-span-3"><h4 class="font-bold">Calcular varias horas</h4><p class="mt-1 text-sm text-app-text-muted">El servidor comprueba cada bloque, sus cierres y la tarifa aplicable.</p></div>
      <SelectControl id="precio-hora-inicio" v-model="horaInicio" label="Hora de inicio" :options="horasDisponibles" placeholder="Selecciona una hora" required />
      <SelectControl id="precio-duracion" v-model="duracion" label="Duración" :options="duraciones" required />
      <button class="admin-button admin-button-primary self-end" :disabled="calculando || !horaInicio">{{ calculando ? 'Calculando…' : 'Calcular total' }}</button>
      <section v-if="resultado" class="rounded-xl border border-brand-lime bg-app-surface-2 p-4 sm:col-span-3" aria-live="polite" aria-label="Resultado de cálculo">
        <div class="flex flex-wrap items-start justify-between gap-3"><div><h5 class="font-bold">{{ resultado.duracion_horas }} {{ resultado.duracion_horas === 1 ? 'hora' : 'horas' }}</h5><p class="mt-1 text-sm text-app-text-muted">{{ horaEtiqueta(resultado.hora_inicio) }}–{{ horaEtiqueta(resultado.hora_fin) }}</p></div><p class="text-right text-2xl font-bold tabular-nums">{{ formatearPEN(resultado.total, resultado.moneda) }}<span class="block text-xs font-medium text-app-text-muted">Total · {{ formatearPEN(resultado.subtotal, resultado.moneda) }} subtotal</span></p></div>
        <ul class="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3"><li v-for="bloque in resultado.bloques" :key="bloque.fecha_inicio" class="rounded-lg border border-app-border p-3 text-sm"><span class="block font-semibold">{{ horaEtiqueta(bloque.fecha_inicio) }}–{{ horaEtiqueta(bloque.fecha_fin) }}</span><span class="text-app-text-muted">{{ bloque.nombre_tarifa }} · {{ formatearPEN(bloque.precio, bloque.moneda) }}</span></li></ul>
      </section>
    </form>
    <p v-else-if="!consultado" class="rounded-xl bg-app-surface-2 p-4 text-sm text-app-text-muted">Elige una fecha para consultar los precios publicados.</p>
  </section>
</template>
