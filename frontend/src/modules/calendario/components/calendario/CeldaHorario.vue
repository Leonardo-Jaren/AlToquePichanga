<script setup>
import { Ban, CheckCircle2, Clock3, Info } from 'lucide-vue-next'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import BotonBase from '@/shared/components/BotonBase.vue'
import { bloquePuedeCotizar, claseEstadoBloque, etiquetaEstadoBloque } from '../../utils/bloques'
import { horaEtiqueta } from '../../utils/fechas'

const props = defineProps({
  canchaId: { type: String, required: true },
  canchaNombre: { type: String, required: true },
  bloque: { type: Object, default: null },
  hora: { type: String, required: true },
  zonaHoraria: { type: String, default: 'America/Lima' },
  seleccionado: { type: Boolean, default: false },
})
const emit = defineEmits(['seleccionar', 'detalle'])

function elegir() {
  emit('seleccionar', { canchaId: props.canchaId, canchaNombre: props.canchaNombre, bloque: props.bloque })
}

function verDetalle() {
  emit('detalle', { ...props.bloque, canchaId: props.canchaId, canchaNombre: props.canchaNombre })
}
</script>

<template>
  <td class="calendar-grid-cell">
    <div v-if="bloque" :class="['calendar-slot', `calendar-slot-${claseEstadoBloque(bloque)}`, seleccionado ? 'calendar-slot-selected' : '']">
      <button v-if="bloquePuedeCotizar(bloque)" class="calendar-slot-action" type="button"
        :aria-pressed="seleccionado"
        :aria-label="`${seleccionado ? 'Quitar' : 'Seleccionar'} ${horaEtiqueta(hora, zonaHoraria)} para cotizar en ${canchaNombre}. El bloque tiene tarifa configurada.`"
        @click="elegir">
        <strong>{{ formatearPEN(bloque.precio, bloque.moneda) }}</strong>
        <span><CheckCircle2 aria-hidden="true" />Con tarifa</span>
      </button>
      <div v-else class="calendar-slot-state">
        <CheckCircle2 v-if="claseEstadoBloque(bloque) === 'success'" aria-hidden="true" />
        <Clock3 v-else-if="claseEstadoBloque(bloque) === 'warning'" aria-hidden="true" />
        <Ban v-else aria-hidden="true" />
        <span>{{ etiquetaEstadoBloque(bloque) }}</span>
      </div>
      <BotonBase variante="texto" tamano="pequeno" class="calendar-slot-detail" :aria-label="`Ver detalle de ${horaEtiqueta(hora, zonaHoraria)} en ${canchaNombre}`" @click="verDetalle">
        <template #icono-inicio><Info aria-hidden="true" /></template>Detalles
      </BotonBase>
    </div>
    <span v-else class="calendar-slot-empty">—<span class="sr-only">Sin horario operativo</span></span>
  </td>
</template>

<style scoped>
.calendar-grid-cell { min-width: 116px; vertical-align: top; }
.calendar-slot { display: flex; min-height: 98px; flex-direction: column; justify-content: space-between; gap: 4px; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 8px; }
.calendar-slot-success { border-color: color-mix(in srgb, var(--status-success-text) 30%, var(--border)); background: var(--status-success-bg); color: var(--status-success-text); }
.calendar-slot-warning { border-color: color-mix(in srgb, var(--status-warning-text) 30%, var(--border)); background: var(--status-warning-bg); color: var(--status-warning-text); }
.calendar-slot-muted { background: var(--surface-2); color: var(--text-muted); }
.calendar-slot-selected { border-color: var(--brand-lime); box-shadow: inset 0 0 0 1px var(--brand-lime); }
.calendar-slot-action { display: grid; min-height: 48px; align-content: center; justify-items: start; gap: 3px; border: 0; border-radius: var(--radius-sm); background: transparent; padding: 2px; color: inherit; text-align: left; cursor: pointer; }
.calendar-slot-action strong { font-size: 14px; font-variant-numeric: tabular-nums; }
.calendar-slot-action span, .calendar-slot-state { display: inline-flex; align-items: center; gap: 5px; font-size: 11px; font-weight: 700; line-height: 1.3; }
.calendar-slot-action svg, .calendar-slot-state svg { height: 14px; width: 14px; flex: 0 0 auto; }
.calendar-slot-detail { min-height: 32px; align-self: flex-start; padding: 3px 2px; color: inherit; font-size: 11px; }
.calendar-slot-detail :deep(svg) { height: 13px; width: 13px; }
.calendar-slot-action:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.calendar-slot-empty { display: grid; min-height: 98px; place-items: center; border: 1px dashed var(--border); border-radius: var(--radius-md); color: var(--text-subtle); }
@media (max-width: 639px) {
  .calendar-grid-cell { min-width: 106px; }
  .calendar-slot { min-height: 92px; padding: 7px; }
}
</style>
