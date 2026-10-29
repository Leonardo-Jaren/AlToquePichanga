<script setup>
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import BotonBase from '@/shared/components/BotonBase.vue'
import { fechaEtiqueta } from '../../utils/fechas'

defineProps({
  vista: { type: String, required: true },
  fecha: { type: String, required: true },
  fechaActiva: { type: String, required: true },
  dias: { type: Array, default: () => [] },
  titulo: { type: String, required: true },
})
const emit = defineEmits(['update:vista', 'update:fecha', 'navegar', 'hoy', 'cambiar-dia'])

function actualizarFecha(evento) {
  emit('update:fecha', evento.target.value)
}

function actualizarVista(valor) {
  emit('update:vista', valor)
}
</script>

<template>
  <section class="calendar-periodo admin-card" aria-label="Controles del calendario">
    <div class="calendar-date-navigation" aria-label="Navegar fechas">
      <BotonBase variante="icono" aria-label="Periodo anterior" @click="emit('navegar', -1)">
        <template #icono-inicio><ChevronLeft aria-hidden="true" /></template>
      </BotonBase>
      <div class="calendar-date-label">
        <CalendarDays aria-hidden="true" />
        <span class="capitalize">{{ titulo }}</span>
      </div>
      <BotonBase variante="icono" aria-label="Periodo siguiente" @click="emit('navegar', 1)">
        <template #icono-inicio><ChevronRight aria-hidden="true" /></template>
      </BotonBase>
    </div>

    <div class="calendar-toolbar-controls">
      <label class="calendar-date-input">
        <span>Fecha</span>
        <input :value="fecha" type="date" aria-label="Fecha de referencia del calendario" @input="actualizarFecha">
      </label>
      <BotonBase tamano="pequeno" @click="emit('hoy')">Hoy</BotonBase>
      <div class="calendar-view-toggle" role="group" aria-label="Vista del calendario">
        <button type="button" :aria-pressed="vista === 'dia'" :class="vista === 'dia' ? 'calendar-view-active' : ''" @click="actualizarVista('dia')">Día</button>
        <button type="button" :aria-pressed="vista === 'semana'" :class="vista === 'semana' ? 'calendar-view-active' : ''" @click="actualizarVista('semana')">Semana</button>
      </div>
    </div>
  </section>

  <div v-if="vista === 'semana'" class="calendar-week-picker" role="group" aria-label="Días de la semana">
    <button v-for="dia in dias" :key="dia" type="button" :aria-pressed="fechaActiva === dia"
      :class="fechaActiva === dia ? 'calendar-week-day-active' : ''" @click="emit('cambiar-dia', dia)">
      <span>{{ fechaEtiqueta(dia) }}</span><strong>{{ dia.slice(8, 10) }}</strong>
    </button>
  </div>
</template>

<style scoped>
.calendar-periodo { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px; }
.calendar-date-navigation, .calendar-toolbar-controls, .calendar-date-label { display: flex; align-items: center; }
.calendar-date-navigation { min-width: 0; gap: 8px; }
.calendar-date-label { min-width: 0; gap: 10px; padding: 0 8px; color: var(--text); font-size: 16px; font-weight: 700; }
.calendar-date-label :deep(svg) { height: 20px; width: 20px; flex: 0 0 auto; color: var(--link); }
.calendar-date-label span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.calendar-toolbar-controls { gap: 8px; }
.calendar-date-input { display: grid; gap: 3px; min-width: 148px; color: var(--text-muted); font-size: 11px; font-weight: 600; }
.calendar-date-input input { min-height: 40px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--input-bg); padding: 6px 9px; color: var(--text); font: 500 13px var(--font-body); }
.calendar-view-toggle { display: flex; align-items: center; gap: 3px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface-2); padding: 3px; }
.calendar-view-toggle button { min-height: 36px; min-width: 56px; border: 0; border-radius: var(--radius-sm); background: transparent; padding: 6px 10px; color: var(--text-muted); font: 600 13px var(--font-body); cursor: pointer; }
.calendar-view-toggle button.calendar-view-active { background: var(--surface); color: var(--text); box-shadow: var(--shadow); }
.calendar-week-picker { display: grid; grid-template-columns: repeat(7, minmax(70px, 1fr)); gap: 8px; }
.calendar-week-picker button { display: grid; min-height: 58px; grid-template-columns: 1fr auto; align-items: center; gap: 8px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface); padding: 8px 12px; color: var(--text-muted); text-align: left; cursor: pointer; }
.calendar-week-picker button span { min-width: 0; overflow: hidden; font-size: 12px; font-weight: 600; text-overflow: ellipsis; text-transform: capitalize; white-space: nowrap; }
.calendar-week-picker button strong { color: var(--text); font-size: 18px; font-variant-numeric: tabular-nums; }
.calendar-week-picker button.calendar-week-day-active { border-color: var(--brand-lime); background: var(--selection-bg); color: var(--text); }
.calendar-week-picker button:focus-visible, .calendar-view-toggle button:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
@media (max-width: 1023px) {
  .calendar-week-picker { overflow-x: auto; grid-template-columns: repeat(7, minmax(82px, 1fr)); padding-bottom: 3px; }
}
@media (max-width: 639px) {
  .calendar-periodo { align-items: stretch; flex-direction: column; padding: 10px; }
  .calendar-date-navigation { justify-content: space-between; }
  .calendar-date-label { font-size: 14px; }
  .calendar-toolbar-controls { display: grid; grid-template-columns: minmax(0, 1fr) auto; }
  .calendar-date-input { grid-column: 1 / -1; }
  .calendar-view-toggle { grid-column: 1 / -1; }
  .calendar-view-toggle button { flex: 1; }
}
</style>
