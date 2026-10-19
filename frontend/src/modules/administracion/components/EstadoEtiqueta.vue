<script setup>
import { computed } from 'vue'

const props = defineProps({ estado: { type: String, required: true } })
const etiquetas = {
  pendiente: ['Pendiente', 'warning'], pendiente_pago: ['Pendiente de pago', 'warning'],
  pendiente_validacion: ['En revisión', 'warning'], activa: ['Activa', 'success'],
  inactiva: ['Inactiva', 'info'], mantenimiento: ['Mantenimiento', 'warning'],
  aprobada: ['Aprobada', 'success'], confirmada: ['Confirmada', 'success'],
  vencida: ['Vencida', 'danger'], suspendida: ['Suspendida', 'danger'],
  rechazada: ['Rechazada', 'danger'], cancelada: ['Cancelada', 'danger'],
  expirada: ['Vencida', 'danger'],
}
const info = computed(() => etiquetas[props.estado] || [props.estado, 'info'])
</script>

<template>
  <span :class="`admin-state admin-state-${info[1]}`">{{ info[0] }}</span>
</template>
