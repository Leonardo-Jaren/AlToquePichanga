<script setup>
import { computed } from 'vue'
import { CalendarClock, MapPin, UserRound } from 'lucide-vue-next'
import BotonBase from '@/shared/components/BotonBase.vue'
import ModalBase from '@/shared/components/ModalBase.vue'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import { fechaEtiqueta, horaEtiqueta } from '@/modules/calendario/utils/fechas'
import { etiquetaEstadoReserva } from '../utils/reservas'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  reserva: { type: Object, default: null },
  cargando: { type: Boolean, default: false },
  administrativa: { type: Boolean, default: false },
})
const emit = defineEmits(['update:modelValue'])
const fecha = computed(() => props.reserva?.inicio?.slice(0, 10) || '')
const tonoEstado = computed(() => ({
  retenida: 'detalle-estado-warning',
  confirmada: 'detalle-estado-success',
  vencida: 'detalle-estado-neutral',
  cancelada: 'detalle-estado-neutral',
}[props.reserva?.estado] || 'detalle-estado-neutral'))
</script>

<template>
  <ModalBase :model-value="modelValue" :titulo="reserva ? `Solicitud ${reserva.codigo}` : 'Detalle de reserva'"
    descripcion="Horario, importe y estado de la solicitud." ancho="mediano"
    @update:model-value="emit('update:modelValue', $event)">
    <p v-if="cargando" class="detalle-reserva-loading" role="status">Cargando detalle…</p>
    <section v-else-if="reserva" class="detalle-reserva">
      <div class="detalle-reserva-heading">
        <span class="detalle-estado" :class="tonoEstado">{{ etiquetaEstadoReserva(reserva.estado) }}</span>
        <p class="detalle-codigo">{{ reserva.codigo }}</p>
      </div>
      <dl class="detalle-reserva-grid">
        <div><dt><MapPin aria-hidden="true" />Cancha y sede</dt><dd>{{ reserva.cancha_nombre }} · {{ reserva.sede_nombre }}</dd></div>
        <div><dt><CalendarClock aria-hidden="true" />Fecha y horario</dt><dd class="capitalize">{{ fechaEtiqueta(fecha, { completa: true }) }} · {{ horaEtiqueta(reserva.inicio) }}–{{ horaEtiqueta(reserva.fin) }}</dd></div>
        <div v-if="administrativa && reserva.jugador"><dt><UserRound aria-hidden="true" />Jugador</dt><dd>{{ reserva.jugador.nombre }}<span v-if="reserva.jugador.correo" class="detalle-reserva-secondary">{{ reserva.jugador.correo }}</span></dd></div>
        <div><dt>Duración</dt><dd>{{ reserva.duracion_horas }} {{ reserva.duracion_horas === 1 ? 'hora' : 'horas' }}</dd></div>
        <div><dt>Importe total</dt><dd>{{ formatearPEN(reserva.importe_total, reserva.moneda) }}</dd></div>
        <div><dt>Adelanto mínimo requerido</dt><dd>{{ formatearPEN(reserva.adelanto_minimo, reserva.moneda) }}</dd></div>
        <div v-if="reserva.estado === 'retenida'"><dt>Retención vence</dt><dd>{{ new Date(reserva.retencion_vence_en).toLocaleString('es-PE', { timeZone: 'America/Lima', hourCycle: 'h23' }) }} · America/Lima</dd></div>
      </dl>
      <section v-if="reserva.cotizacion_aplicada?.bloques?.length" class="detalle-cotizacion" aria-label="Desglose de precio aplicado">
        <h3>Desglose guardado</h3>
        <ul>
          <li v-for="bloque in reserva.cotizacion_aplicada.bloques" :key="bloque.fecha_inicio">
            <span>{{ horaEtiqueta(bloque.fecha_inicio) }}–{{ horaEtiqueta(bloque.fecha_fin) }}</span>
            <span>{{ bloque.nombre_tarifa || bloque.tipo_tarifa }} · {{ formatearPEN(bloque.precio, bloque.moneda) }}</span>
          </li>
        </ul>
      </section>
      <p class="detalle-reserva-note">La retención aparta el horario temporalmente. No registra un pago ni confirma la reserva.</p>
    </section>
    <p v-else class="detalle-reserva-loading">No se encontró el detalle solicitado.</p>
    <template #pie>
      <slot name="acciones" />
      <BotonBase @click="emit('update:modelValue', false)">Cerrar</BotonBase>
    </template>
  </ModalBase>
</template>

<style scoped>
.detalle-reserva-loading { margin: 0; padding: 18px; color: var(--text-muted); }
.detalle-reserva { display: grid; gap: 18px; }
.detalle-reserva-heading { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; }
.detalle-estado { border-radius: 999px; padding: 6px 10px; font-size: 12px; font-weight: 700; }
.detalle-estado-warning { background: var(--warning-bg); color: var(--warning); }
.detalle-estado-success { background: var(--success-bg); color: var(--success); }
.detalle-estado-neutral { background: var(--surface-2); color: var(--text-muted); }
.detalle-codigo { margin: 0; color: var(--text-muted); font: 600 13px/1.4 ui-monospace, monospace; }
.detalle-reserva-grid { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 14px; margin: 0; }
.detalle-reserva-grid > div { min-width: 0; border-radius: var(--radius-md); background: var(--surface-2); padding: 12px; }
.detalle-reserva-grid dt { display: flex; align-items: center; gap: 7px; color: var(--text-muted); font-size: 12px; }
.detalle-reserva-grid dt :deep(svg) { width: 15px; height: 15px; color: var(--link); }
.detalle-reserva-grid dd { margin: 5px 0 0; color: var(--text); font-size: 14px; font-weight: 600; overflow-wrap: anywhere; }
.detalle-reserva-secondary { display: block; margin-top: 3px; color: var(--text-muted); font-size: 12px; font-weight: 400; }
.detalle-cotizacion { border-top: 1px solid var(--border); padding-top: 14px; }
.detalle-cotizacion h3 { margin: 0; font: 700 15px/1.3 var(--font-body); }
.detalle-cotizacion ul { display: grid; gap: 7px; margin: 10px 0 0; padding: 0; list-style: none; }
.detalle-cotizacion li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px; border-radius: var(--radius-sm); background: var(--surface-2); padding: 9px 11px; color: var(--text-muted); font-size: 12px; }
.detalle-cotizacion li span:first-child { color: var(--text); font-weight: 700; font-variant-numeric: tabular-nums; }
.detalle-reserva-note { margin: 0; border-left: 3px solid var(--brand-lime); padding-left: 10px; color: var(--text-muted); font-size: 12px; line-height: 1.45; }
@media (max-width: 639px) { .detalle-reserva-grid { grid-template-columns: minmax(0,1fr); } }
</style>
