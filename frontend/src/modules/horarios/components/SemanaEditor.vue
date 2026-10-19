<script setup>
import { computed } from 'vue'
import { Plus, X } from 'lucide-vue-next'
import { DIAS_SEMANA, normalizarIntervalos } from '../utils/horarios'

const props = defineProps({
  titulo: { type: String, required: true },
  descripcion: { type: String, default: '' },
  intervalos: { type: Array, default: () => [] },
  marcoIntervalos: { type: Array, default: null },
  diasHeredados: { type: Array, default: () => [] },
  permiteHerencia: { type: Boolean, default: false },
  editable: { type: Boolean, default: true },
})
const emit = defineEmits(['actualizar', 'heredar-dia'])
const diasConIntervalos = computed(() => DIAS_SEMANA.map((dia) => ({
  ...dia,
  intervalos: normalizarIntervalos(props.intervalos).filter((item) => item.dia_semana === dia.id),
  marco: normalizarIntervalos(props.marcoIntervalos || []).filter((item) => item.dia_semana === dia.id),
  heredado: props.diasHeredados.map(Number).includes(dia.id),
})))

function reemplazarDia(dia, intervalosDia) {
  const otros = props.intervalos.filter((item) => Number(item.dia_semana) !== dia)
  emit('actualizar', normalizarIntervalos([...otros, ...intervalosDia]))
}
function agregar(dia) {
  const delDia = diasConIntervalos.value.find((item) => item.id === dia).intervalos
  reemplazarDia(dia, [...delDia, { dia_semana: dia, hora_apertura: '08:00', hora_cierre: '22:00' }])
}
function actualizar(dia, indice, campo, valor) {
  const delDia = diasConIntervalos.value.find((item) => item.id === dia).intervalos
  reemplazarDia(dia, delDia.map((item, posicion) => posicion === indice ? { ...item, [campo]: valor } : item))
}
function quitar(dia, indice) {
  const delDia = diasConIntervalos.value.find((item) => item.id === dia).intervalos
  reemplazarDia(dia, delDia.filter((_, posicion) => posicion !== indice))
}
function cerrado(dia) { reemplazarDia(dia, []) }
function intervalosVisibles(dia) { return dia.heredado ? dia.marco : dia.intervalos }
</script>

<template>
  <section class="space-y-4" :aria-label="titulo">
    <header>
      <h3 class="text-lg font-bold">{{ titulo }}</h3>
      <p v-if="descripcion" class="mt-1 text-sm text-app-text-muted">{{ descripcion }}</p>
    </header>
    <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <article v-for="dia in diasConIntervalos" :key="dia.id" class="rounded-xl border border-app-border bg-app-surface p-3 sm:p-4">
        <div class="mb-3 flex min-h-11 items-center justify-between gap-2 border-b border-app-border pb-3">
          <h4 class="font-bold">{{ dia.nombre }}</h4>
          <button v-if="permiteHerencia && editable" class="admin-button admin-button-secondary px-3" type="button" :aria-label="dia.heredado ? `Personalizar ${dia.nombre}` : `Heredar horario de sede para ${dia.nombre}`" @click="emit('heredar-dia', dia.id)">
            {{ dia.heredado ? 'Personalizar día' : 'Heredar sede' }}
          </button>
          <button v-else-if="editable && !permiteHerencia" class="admin-button admin-button-secondary px-3" type="button" :aria-label="dia.intervalos.length ? `Cerrar ${dia.nombre}` : `Abrir ${dia.nombre}`" @click="dia.intervalos.length ? cerrado(dia.id) : agregar(dia.id)">
            {{ dia.intervalos.length ? 'Cerrar día' : 'Abrir día' }}
          </button>
          <span v-else class="text-sm font-semibold text-app-text-muted">{{ dia.heredado ? 'Heredado de sede' : (intervalosVisibles(dia).length ? (permiteHerencia ? 'Personalizado' : 'Abierto') : 'Cerrado') }}</span>
        </div>

        <div v-if="marcoIntervalos" class="mb-3 rounded-lg border border-app-border-strong bg-app-surface-2 p-2.5">
          <p class="text-xs font-semibold text-app-text-muted">Marco de sede</p>
          <p v-if="dia.marco.length" class="mt-1 text-sm tabular-nums">
            <span v-for="(item, indice) in dia.marco" :key="`marco-${indice}`" class="block">{{ item.hora_apertura }}–{{ item.hora_cierre }}<span v-if="item.hora_cierre < item.hora_apertura" class="ml-1 text-app-text-muted">(día siguiente)</span></span>
          </p>
          <p v-else class="mt-1 text-sm text-app-text-muted">Sede cerrada</p>
        </div>

        <div v-if="intervalosVisibles(dia).length" class="space-y-2">
          <div v-for="(item, indice) in intervalosVisibles(dia)" :key="`${dia.id}-${indice}`" class="rounded-lg border border-brand-lime bg-app-selection p-2.5">
            <p v-if="marcoIntervalos" class="mb-2 text-xs font-semibold text-app-text-muted">{{ dia.heredado ? 'Carril heredado de sede' : 'Carril propio de cancha' }}</p>
            <div class="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_44px] items-end gap-2">
              <label class="min-w-0">
                <span class="admin-label text-xs">Abre</span>
                <input class="admin-field px-2 tabular-nums" type="time" :value="item.hora_apertura" :disabled="!editable || dia.heredado" :aria-label="`${dia.nombre}, intervalo ${indice + 1}, hora de apertura`" @input="actualizar(dia.id, indice, 'hora_apertura', $event.target.value)">
              </label>
              <label class="min-w-0">
                <span class="admin-label text-xs">Cierra</span>
                <input class="admin-field px-2 tabular-nums" type="time" :value="item.hora_cierre" :disabled="!editable || dia.heredado" :aria-label="`${dia.nombre}, intervalo ${indice + 1}, hora de cierre`" @input="actualizar(dia.id, indice, 'hora_cierre', $event.target.value)">
              </label>
              <button v-if="editable && !dia.heredado" class="admin-button admin-button-quiet min-h-11 px-2" type="button" :aria-label="`Quitar intervalo ${indice + 1} de ${dia.nombre}`" @click="quitar(dia.id, indice)"><X aria-hidden="true" class="size-4" /></button>
            </div>
            <p v-if="item.hora_cierre < item.hora_apertura" class="mt-2 text-xs text-app-text-muted">El cierre es al día siguiente.</p>
          </div>
          <button v-if="editable && !dia.heredado" class="admin-button admin-button-secondary min-h-11 w-full" type="button" @click="agregar(dia.id)"><Plus aria-hidden="true" class="size-4" />{{ permiteHerencia ? 'Añadir intervalo propio' : 'Añadir intervalo' }}</button>
        </div>
        <div v-else-if="dia.heredado" class="rounded-lg border border-dashed border-app-border-strong bg-app-surface-2 px-3 py-4 text-center text-sm text-app-text-muted">La sede está cerrada</div>
        <div v-else class="rounded-lg border border-dashed border-app-border-strong bg-app-surface-2 px-3 py-4 text-center text-sm text-app-text-muted">
          <p>Cerrado</p>
          <button v-if="editable && permiteHerencia && !dia.heredado" class="admin-button admin-button-secondary mt-3 min-h-11 w-full" type="button" @click="agregar(dia.id)"><Plus aria-hidden="true" class="size-4" />Añadir intervalo propio</button>
        </div>
      </article>
    </div>
    <p class="text-xs text-app-text-muted">Las horas usan el horario local de Perú (America/Lima). Un cierre anterior a la apertura termina al día siguiente.</p>
  </section>
</template>
