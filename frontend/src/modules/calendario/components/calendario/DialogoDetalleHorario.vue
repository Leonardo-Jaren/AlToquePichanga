<script setup>
import ModalBase from '@/shared/components/ModalBase.vue'
import DetalleBloqueHorario from './DetalleBloqueHorario.vue'

defineProps({
  modelValue: { type: Boolean, default: false },
  detalle: { type: Object, default: null },
  zonaHoraria: { type: String, default: 'America/Lima' },
})
const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <ModalBase
    :model-value="modelValue"
    titulo="Detalle del horario"
    descripcion="Información operativa del bloque seleccionado."
    ancho="pequeno"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <DetalleBloqueHorario :detalle="detalle" :zona-horaria="zonaHoraria" />
    <p class="calendar-detail-dialog-note">Este detalle no confirma una reserva ni bloquea el horario.</p>
  </ModalBase>
</template>

<style scoped>
.calendar-detail-dialog-note { margin: 12px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.45; }
</style>
