<script setup>
defineProps({
  titulo: { type: String, required: true },
  valor: { type: [Number, String], required: true },
  descripcion: { type: String, required: true },
  icono: { type: [Object, Function], required: true },
  tono: { type: String, default: 'marca' },
})
</script>

<template>
  <article class="calendar-stat-card" :class="`calendar-stat-${tono}`">
    <span class="calendar-stat-icon"><component :is="icono" aria-hidden="true" /></span>
    <div>
      <p>{{ titulo }}</p>
      <strong>{{ valor }}</strong>
      <small>{{ descripcion }}</small>
    </div>
  </article>
</template>

<style scoped>
.calendar-stat-card { display: flex; min-width: 0; align-items: flex-start; gap: 12px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 16px; box-shadow: var(--shadow); }
.calendar-stat-icon { display: grid; height: 40px; width: 40px; flex: 0 0 auto; place-items: center; border-radius: var(--radius-md); background: var(--selection-bg); color: var(--link); }
.calendar-stat-icon :deep(svg) { height: 20px; width: 20px; }
.calendar-stat-card p { margin: 0; color: var(--text-muted); font-size: 12px; font-weight: 700; }
.calendar-stat-card strong { display: block; margin-top: 4px; color: var(--text); font-size: 26px; font-weight: 700; line-height: 1.1; font-variant-numeric: tabular-nums; }
.calendar-stat-card small { display: block; margin-top: 5px; color: var(--text-subtle); font-size: 11px; line-height: 1.35; }
.calendar-stat-exito .calendar-stat-icon { background: var(--status-success-bg); color: var(--status-success-text); }
.calendar-stat-tarifa .calendar-stat-icon { background: var(--status-warning-bg); color: var(--status-warning-text); }
.calendar-stat-info .calendar-stat-icon { background: var(--status-info-bg); color: var(--status-info-text); }
@media (max-width: 639px) {
  .calendar-stat-card { gap: 9px; padding: 12px 10px; }
  .calendar-stat-icon { height: 34px; width: 34px; }
  .calendar-stat-icon :deep(svg) { height: 17px; width: 17px; }
  .calendar-stat-card p { font-size: 11px; }
  .calendar-stat-card strong { font-size: 22px; }
  .calendar-stat-card small { font-size: 10px; }
}
</style>
