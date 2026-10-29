<script setup>
import { Ban, CheckCircle2, Clock3 } from 'lucide-vue-next'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import { etiquetaEstadoBloque } from '../../utils/bloques'
import { fechaEtiqueta, horaEtiqueta } from '../../utils/fechas'

const props = defineProps({
  detalle: { type: Object, default: null },
  zonaHoraria: { type: String, default: 'America/Lima' },
})
</script>

<template>
  <section v-if="detalle" class="calendar-detail-card" aria-live="polite">
    <div class="calendar-detail-topline">
      <span class="calendar-detail-state" :class="detalle.habilitada_operativamente ? 'calendar-detail-state-operativo' : 'calendar-detail-state-cerrado'">
        <CheckCircle2 v-if="detalle.habilitada_operativamente" aria-hidden="true" />
        <Ban v-else aria-hidden="true" />
        {{ etiquetaEstadoBloque(detalle) }}
      </span>
      <span v-if="detalle.origen === 'ampliacion_excepcional'" class="calendar-detail-exception">Excepción</span>
    </div>
    <h3>{{ detalle.canchaNombre || 'Cancha' }}</h3>
    <p class="calendar-detail-date">{{ fechaEtiqueta(detalle.fecha_inicio.slice(0, 10), { completa: true }) }}</p>
    <p class="calendar-detail-time"><Clock3 aria-hidden="true" />{{ horaEtiqueta(detalle.fecha_inicio, zonaHoraria) }}–{{ horaEtiqueta(detalle.fecha_fin, zonaHoraria) }}</p>
    <dl class="calendar-detail-values">
      <div><dt>Estado del horario</dt><dd>{{ detalle.estado }}</dd></div>
      <div v-if="detalle.estado_reserva"><dt>Estado de reserva</dt><dd>{{ detalle.estado_reserva === 'retenida' ? 'Retenida temporalmente' : 'Ocupada por una reserva' }}</dd></div>
      <div><dt>Precio por bloque</dt><dd>{{ detalle.precio ? formatearPEN(detalle.precio, detalle.moneda) : 'Sin precio' }}</dd></div>
      <div v-if="detalle.tipo_tarifa"><dt>Tipo de tarifa</dt><dd>{{ detalle.tipo_tarifa.replaceAll('_', ' ') }}</dd></div>
      <div v-if="detalle.motivo" class="calendar-detail-motivo"><dt>Motivo registrado</dt><dd>{{ detalle.motivo }}</dd></div>
    </dl>
  </section>
</template>

<style scoped>
.calendar-detail-card { border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface-2); padding: 14px; }
.calendar-detail-topline { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px; }
.calendar-detail-state { display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 5px 9px; font-size: 11px; font-weight: 700; }
.calendar-detail-state :deep(svg) { height: 14px; width: 14px; }
.calendar-detail-state-operativo { background: var(--status-success-bg); color: var(--status-success-text); }
.calendar-detail-state-cerrado { background: var(--status-warning-bg); color: var(--status-warning-text); }
.calendar-detail-exception { border-radius: 999px; background: var(--status-info-bg); padding: 5px 9px; color: var(--status-info-text); font-size: 11px; font-weight: 700; }
.calendar-detail-card h3 { margin: 14px 0 0; color: var(--text); font: 700 16px/1.35 var(--font-body); overflow-wrap: anywhere; }
.calendar-detail-date { margin: 3px 0 0; color: var(--text-muted); font-size: 13px; text-transform: capitalize; }
.calendar-detail-time { display: flex; align-items: center; gap: 7px; margin: 12px 0; color: var(--link); font-size: 15px; font-weight: 700; font-variant-numeric: tabular-nums; }
.calendar-detail-time :deep(svg) { height: 17px; width: 17px; }
.calendar-detail-values { display: grid; gap: 10px; border-top: 1px solid var(--border); margin: 12px 0 0; padding-top: 12px; }
.calendar-detail-values div { min-width: 0; }
.calendar-detail-values dt { color: var(--text-muted); font-size: 12px; }
.calendar-detail-values dd { margin: 2px 0 0; color: var(--text); font-size: 13px; font-weight: 600; overflow-wrap: anywhere; text-transform: capitalize; }
.calendar-detail-motivo { border-radius: var(--radius-sm); background: var(--surface); padding: 9px; }
</style>
