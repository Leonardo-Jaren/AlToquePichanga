<script setup>
import { CalendarDays, Info } from 'lucide-vue-next'
import { horaEtiqueta } from '../../utils/fechas'
import CeldaHorario from './CeldaHorario.vue'

const props = defineProps({
  filas: { type: Array, default: () => [] },
  horas: { type: Array, default: () => [] },
  zonaHoraria: { type: String, default: 'America/Lima' },
  seleccion: { type: Array, default: () => [] },
})
const emit = defineEmits(['seleccionar', 'detalle'])

function estaSeleccionado(fila, bloque) {
  return props.seleccion.some((item) => item.canchaId === fila.id && item.fecha_inicio === bloque.fecha_inicio)
}

</script>

<template>
  <section class="admin-card calendar-matrix-card" aria-labelledby="matriz-horaria-titulo">
    <header class="calendar-matrix-heading">
      <div>
        <div class="calendar-section-title">
          <CalendarDays aria-hidden="true" class="size-5" />
          <h2 id="matriz-horaria-titulo">Matriz horaria</h2>
        </div>
        <p class="calendar-matrix-description">Bloques de una hora por cancha, con retenciones vigentes y precios configurados.</p>
      </div>
      <span class="calendar-grid-count">{{ filas.length }} {{ filas.length === 1 ? 'cancha' : 'canchas' }}</span>
    </header>

    <div class="calendar-legend" aria-label="Leyenda de estados">
      <span><i class="calendar-legend-dot calendar-legend-operativo" aria-hidden="true" />Libre para reservar</span>
      <span><i class="calendar-legend-dot calendar-legend-alerta" aria-hidden="true" />Retenido u ocupado</span>
      <span><i class="calendar-legend-dot calendar-legend-alerta" aria-hidden="true" />Revisar tarifa</span>
      <span><i class="calendar-legend-dot calendar-legend-cerrado" aria-hidden="true" />Cerrado o inactivo</span>
      <span><i class="calendar-legend-dot calendar-legend-seleccionado" aria-hidden="true" />Seleccionado</span>
    </div>

    <div class="calendar-table-scroll" role="region" aria-label="Matriz de horarios por cancha" tabindex="0">
      <table class="calendar-grid">
        <thead>
          <tr>
            <th class="calendar-grid-court" scope="col">Cancha / instalación</th>
            <th v-for="hora in horas" :key="hora" class="calendar-grid-time" scope="col">
              {{ horaEtiqueta(hora, zonaHoraria) }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="fila in filas" :key="fila.id">
            <th class="calendar-grid-court calendar-grid-row-title" scope="row">
              <span class="calendar-court-name">{{ fila.nombre }}</span>
              <span v-if="fila.estado && fila.estado !== 'activa'" class="calendar-court-state">{{ fila.estado === 'mantenimiento' ? 'En mantenimiento' : 'Inactiva' }}</span>
            </th>
            <CeldaHorario v-for="hora in horas" :key="`${fila.id}-${hora}`" :cancha-id="fila.id"
              :cancha-nombre="fila.nombre" :bloque="fila.mapaBloques[hora]" :hora="hora"
              :zona-horaria="zonaHoraria" :seleccionado="fila.mapaBloques[hora] ? estaSeleccionado(fila, fila.mapaBloques[hora]) : false"
              @seleccionar="emit('seleccionar', $event)" @detalle="emit('detalle', $event)" />
          </tr>
        </tbody>
      </table>
    </div>

    <p class="calendar-matrix-footnote"><Info aria-hidden="true" class="size-4 shrink-0" /> La base de datos valida la disponibilidad al crear cada retención; esta matriz se vuelve a consultar para reflejar cambios.</p>
  </section>
</template>

<style scoped>
.calendar-matrix-card { min-width: 0; padding: 0; overflow: hidden; }
.calendar-matrix-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 20px 20px 14px; }
.calendar-section-title { display: flex; align-items: center; gap: 10px; color: var(--link); }
.calendar-section-title h2 { margin: 0; color: var(--text); font: 700 18px/1.3 var(--font-body); }
.calendar-matrix-description { margin: 5px 0 0; color: var(--text-muted); font-size: 13px; line-height: 1.4; }
.calendar-grid-count { flex: 0 0 auto; border-radius: 999px; background: var(--surface-2); padding: 6px 10px; color: var(--text-muted); font-size: 12px; font-weight: 700; }
.calendar-legend { display: flex; flex-wrap: wrap; gap: 8px 16px; border-bottom: 1px solid var(--border); padding: 0 20px 14px; color: var(--text-muted); font-size: 12px; font-weight: 600; }
.calendar-legend span { display: inline-flex; align-items: center; gap: 7px; }
.calendar-legend-dot { height: 10px; width: 10px; border-radius: 50%; }
.calendar-legend-operativo { background: var(--status-success-text); }
.calendar-legend-alerta { background: var(--status-warning-text); }
.calendar-legend-cerrado { background: var(--text-subtle); }
.calendar-legend-seleccionado { background: var(--brand-lime); }
.calendar-table-scroll { max-width: 100%; overflow: auto; overscroll-behavior-inline: contain; }
.calendar-grid { width: 100%; min-width: max-content; border-collapse: separate; border-spacing: 4px; padding: 8px 12px 12px; text-align: left; }
.calendar-grid th { color: var(--text-muted); font-size: 12px; font-weight: 700; }
.calendar-grid-time { min-width: 116px; padding: 7px 8px; text-align: center; font-variant-numeric: tabular-nums; }
.calendar-grid-court { position: sticky; left: 0; z-index: 2; width: 190px; min-width: 190px; max-width: 190px; background: var(--surface); padding: 8px 12px; }
.calendar-grid thead .calendar-grid-court { z-index: 3; }
.calendar-grid-row-title { border-bottom: 1px solid var(--border); color: var(--text); font-size: 14px; }
.calendar-court-name { display: block; overflow-wrap: anywhere; font-size: 14px; font-weight: 700; }
.calendar-court-state { display: inline-block; margin-top: 6px; color: var(--status-warning-text); font-size: 11px; font-weight: 700; }
.calendar-matrix-footnote { display: flex; align-items: flex-start; gap: 8px; border-top: 1px solid var(--border); margin: 0; padding: 12px 20px 16px; color: var(--text-muted); font-size: 12px; line-height: 1.45; }
@media (max-width: 639px) {
  .calendar-matrix-heading { padding: 16px 14px 12px; }
  .calendar-legend { gap: 8px 12px; padding: 0 14px 12px; }
  .calendar-grid { border-spacing: 3px; padding: 6px 8px 10px; }
  .calendar-grid-court { width: 144px; min-width: 144px; max-width: 144px; padding: 6px 8px; }
  .calendar-grid-time, .calendar-grid-cell { min-width: 106px; }
  .calendar-matrix-footnote { padding: 11px 14px 14px; }
}
</style>
