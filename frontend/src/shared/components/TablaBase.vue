<script setup>
defineProps({
  columnas: { type: Array, required: true },
  filas: { type: Array, default: () => [] },
  clave: { type: String, default: 'id' },
  cargando: { type: Boolean, default: false },
  vacio: { type: String, default: 'No hay resultados para mostrar.' },
  etiqueta: { type: String, default: 'Resultados' },
})
</script>

<template>
  <div class="tabla-base-scroll" role="region" :aria-label="etiqueta" tabindex="0" :aria-busy="cargando">
    <table class="tabla-base">
      <caption class="sr-only">{{ etiqueta }}</caption>
      <thead>
        <tr>
          <th v-for="columna in columnas" :key="columna.key" scope="col" :class="columna.clase">
            {{ columna.label }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="cargando"><td :colspan="columnas.length" class="tabla-base-vacio" role="status">Cargando…</td></tr>
        <tr v-else-if="!filas.length"><td :colspan="columnas.length" class="tabla-base-vacio">{{ vacio }}</td></tr>
        <tr v-for="fila in cargando ? [] : filas" :key="fila[clave]">
          <td v-for="columna in columnas" :key="columna.key" :class="columna.clase">
            <slot :name="`celda-${columna.key}`" :fila="fila" :valor="fila[columna.key]">
              {{ fila[columna.key] ?? '—' }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.tabla-base-scroll { max-width: 100%; overflow: auto; border: 1px solid var(--border); border-radius: var(--radius-md); overscroll-behavior-inline: contain; }
.tabla-base-scroll:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.tabla-base { width: 100%; border-collapse: separate; border-spacing: 0; text-align: left; }
.tabla-base th { position: sticky; top: 0; z-index: 1; background: var(--surface-2); color: var(--text-muted); font-size: 12px; font-weight: 700; white-space: nowrap; }
.tabla-base th, .tabla-base td { padding: 12px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.tabla-base td { color: var(--text); font-size: 13px; }
.tabla-base tbody tr:last-child td { border-bottom: 0; }
.tabla-base tbody tr:hover td { background: color-mix(in srgb, var(--surface-2) 68%, transparent); }
.tabla-base-vacio { height: 100px; color: var(--text-muted) !important; text-align: center; }
@media (max-width: 639px) { .tabla-base th, .tabla-base td { padding: 10px 11px; } }
</style>
