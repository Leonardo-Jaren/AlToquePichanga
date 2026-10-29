<script setup>
import { computed } from 'vue'
import { Ban, CalendarClock, CheckCircle2, Clock3 } from 'lucide-vue-next'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import BotonBase from '@/shared/components/BotonBase.vue'
import { bloquePuedeCotizar, claseEstadoBloque, etiquetaEstadoBloque } from '../../utils/bloques'
import { horaEtiqueta } from '../../utils/fechas'

const props = defineProps({
  bloque: { type: Object, required: true },
  zonaHoraria: { type: String, default: 'America/Lima' },
  seleccionado: { type: Boolean, default: false },
  publico: { type: Boolean, default: false },
})
const emit = defineEmits(['detalle', 'seleccionar'])

const puedeCotizar = computed(() => bloquePuedeCotizar(props.bloque))
const estado = computed(() => etiquetaEstadoBloque(props.bloque))
const tonosEstado = {
  success: 'bg-[var(--status-success-bg)] text-[var(--status-success-text)]',
  warning: 'bg-[var(--status-warning-bg)] text-[var(--status-warning-text)]',
  muted: 'bg-app-surface-2 text-app-text-muted',
}
const tonoEstado = computed(() => tonosEstado[claseEstadoBloque(props.bloque)])
const IconoEstado = computed(() => (
  puedeCotizar.value ? CheckCircle2
    : ['retenida', 'ocupada'].includes(props.bloque.estado) || props.bloque.habilitada_operativamente ? Clock3 : Ban
))
</script>

<template>
  <article data-testid="bloque-calendario" :data-inicio="bloque.fecha_inicio" class="min-w-0 rounded-xl border p-3 transition-colors" :class="seleccionado ? 'border-brand-lime bg-app-surface-2 ring-1 ring-brand-lime' : 'border-app-border bg-app-surface'">
    <div class="flex flex-wrap items-start justify-between gap-2">
      <p class="font-semibold tabular-nums">{{ horaEtiqueta(bloque.fecha_inicio, zonaHoraria) }}–{{ horaEtiqueta(bloque.fecha_fin, zonaHoraria) }}</p>
      <strong v-if="bloque.precio && bloque.tarifa_estado === 'configurada'" class="shrink-0 tabular-nums">{{ formatearPEN(bloque.precio, bloque.moneda) }}</strong>
      <span v-else class="shrink-0 text-sm text-app-text-muted">Sin precio</span>
    </div>
    <p class="mt-2 flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold" :class="tonoEstado">
      <component :is="IconoEstado" aria-hidden="true" class="size-3.5 shrink-0" />
      <span>{{ estado }}</span>
    </p>
    <p v-if="bloque.motivo" class="mt-2 break-words text-xs text-app-text-muted">{{ bloque.motivo }}</p>
    <p v-if="bloque.origen === 'ampliacion_excepcional'" class="mt-2 flex items-center gap-1 text-xs font-medium text-app-link">
      <CalendarClock aria-hidden="true" class="size-3.5" /> Ampliación excepcional
    </p>
    <div class="mt-2 flex flex-wrap gap-2">
      <BotonBase variante="texto" tamano="pequeno" @click="emit('detalle', bloque)">Ver detalles</BotonBase>
      <BotonBase v-if="puedeCotizar" :variante="seleccionado ? 'primario' : 'secundario'" tamano="pequeno" :aria-pressed="seleccionado" @click="emit('seleccionar', bloque)">
        {{ seleccionado ? 'Quitar de la selección' : publico ? 'Seleccionar horario' : 'Agregar a cotización' }}
      </BotonBase>
    </div>
  </article>
</template>
