<script setup>
defineProps({
  variante: { type: String, default: 'secundario' },
  tamano: { type: String, default: 'normal' },
  tipo: { type: String, default: 'button' },
  deshabilitado: { type: Boolean, default: false },
  cargando: { type: Boolean, default: false },
  ariaLabel: { type: String, default: undefined },
})
</script>

<template>
  <button
    class="boton-base"
    :class="[`boton-base-${variante}`, `boton-base-${tamano}`]"
    :type="tipo"
    :disabled="deshabilitado || cargando"
    :aria-label="ariaLabel"
    :aria-busy="cargando ? 'true' : undefined"
  >
    <slot name="icono-inicio" />
    <span v-if="$slots.default"><slot /></span>
    <slot name="icono-fin" />
  </button>
</template>

<style scoped>
.boton-base {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  padding: 9px 15px;
  font: 600 14px/1.2 var(--font-body);
  text-align: center;
  cursor: pointer;
  transition: background-color .15s ease, border-color .15s ease, color .15s ease;
}
.boton-base svg { width: 17px; height: 17px; flex: 0 0 auto; }
.boton-base:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.boton-base:disabled { cursor: not-allowed; opacity: .6; }
.boton-base-primario { background: var(--brand-lime); color: var(--on-brand-lime); }
.boton-base-primario:hover:not(:disabled) { background: var(--brand-lime-hover); }
.boton-base-secundario { border-color: var(--border); background: var(--surface-2); color: var(--text); }
.boton-base-secundario:hover:not(:disabled) { background: var(--surface-3); }
.boton-base-texto { background: transparent; color: var(--link); text-decoration: underline; text-underline-offset: 2px; }
.boton-base-texto:hover:not(:disabled) { background: var(--selection-bg); }
.boton-base-icono { width: 44px; padding: 0; border-color: var(--border); background: var(--surface-2); color: var(--text); }
.boton-base-icono:hover:not(:disabled) { background: var(--surface-3); }
.boton-base-pequeno { min-height: 36px; gap: 6px; padding: 6px 10px; font-size: 12px; }
.boton-base-pequeno svg { width: 15px; height: 15px; }
.boton-base-grande { min-height: 48px; padding: 12px 19px; font-size: 15px; }
@media (prefers-reduced-motion: reduce) {
  .boton-base { transition: none; }
}
</style>
