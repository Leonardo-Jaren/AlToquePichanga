<script setup>
import { getCurrentInstance, nextTick, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import BotonBase from './BotonBase.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  titulo: { type: String, required: true },
  descripcion: { type: String, default: '' },
  ancho: { type: String, default: 'mediano' },
  cerrarAlFondo: { type: Boolean, default: true },
})
const emit = defineEmits(['update:modelValue', 'cerrar'])
const dialogo = ref(null)
const idInstancia = getCurrentInstance()?.uid ?? 'modal'
const tituloId = `modal-titulo-${idInstancia}`
const descripcionId = `modal-descripcion-${idInstancia}`

watch(() => props.modelValue, sincronizarVisibilidad, { immediate: true })

async function sincronizarVisibilidad(abierto) {
  await nextTick()
  const elemento = dialogo.value
  if (!elemento) return
  if (abierto && !elemento.open) elemento.showModal()
  if (!abierto && elemento.open) elemento.close()
}

function cerrar() {
  emit('update:modelValue', false)
}

function sincronizarCierre() {
  emit('update:modelValue', false)
  emit('cerrar')
}

function cerrarAlHacerClic(evento) {
  if (props.cerrarAlFondo && evento.target === dialogo.value) cerrar()
}
</script>

<template>
  <dialog
    ref="dialogo"
    class="modal-base"
    :class="`modal-base-${ancho}`"
    :aria-labelledby="tituloId"
    :aria-describedby="descripcion ? descripcionId : undefined"
    @cancel.prevent="cerrar"
    @close="sincronizarCierre"
    @click="cerrarAlHacerClic"
  >
    <header class="modal-base-cabecera">
      <div>
        <h2 :id="tituloId">{{ titulo }}</h2>
        <p v-if="descripcion" :id="descripcionId">{{ descripcion }}</p>
      </div>
      <BotonBase variante="icono" tamano="pequeno" aria-label="Cerrar diálogo" @click="cerrar">
        <template #icono-inicio><X aria-hidden="true" /></template>
      </BotonBase>
    </header>
    <div class="modal-base-contenido"><slot /></div>
    <footer v-if="$slots.pie" class="modal-base-pie"><slot name="pie" /></footer>
  </dialog>
</template>

<style scoped>
.modal-base {
  width: min(100% - 32px, 560px);
  max-height: min(88vh, 780px);
  overflow: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  background: var(--surface);
  padding: 0;
  color: var(--text);
  box-shadow: var(--shadow);
}
.modal-base::backdrop { background: color-mix(in srgb, var(--brand-charcoal) 72%, transparent); }
.modal-base-grande { width: min(100% - 32px, 820px); }
.modal-base-pequeno { width: min(100% - 32px, 420px); }
.modal-base-cabecera { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; border-bottom: 1px solid var(--border); padding: 20px 22px 16px; }
.modal-base-cabecera h2 { margin: 0; color: var(--text); font: 700 20px/1.3 var(--font-body); }
.modal-base-cabecera p { margin: 5px 0 0; color: var(--text-muted); font-size: 14px; line-height: 1.45; }
.modal-base-cabecera :deep(.boton-base) { min-height: 40px; width: 40px; }
.modal-base-contenido { padding: 18px 22px; }
.modal-base-pie { display: flex; justify-content: flex-end; gap: 8px; border-top: 1px solid var(--border); padding: 14px 22px 18px; }
@media (max-width: 639px) {
  .modal-base { width: calc(100% - 20px); max-height: 90vh; border-radius: var(--radius-lg); }
  .modal-base-cabecera { padding: 16px 16px 13px; }
  .modal-base-contenido { padding: 14px 16px; }
  .modal-base-pie { padding: 12px 16px 14px; }
}
</style>
