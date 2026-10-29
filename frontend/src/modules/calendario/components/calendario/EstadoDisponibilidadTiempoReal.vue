<script setup>
import { computed } from 'vue'
import { Radio, RefreshCw } from 'lucide-vue-next'
import BotonBase from '@/shared/components/BotonBase.vue'

const props = defineProps({
  estado: { type: String, default: 'conectando' },
  sincronizadoEn: { type: String, default: '' },
  cargando: { type: Boolean, default: false },
})
defineEmits(['actualizar'])

const mensaje = computed(() => {
  if (props.cargando) return 'Sincronizando disponibilidad…'
  if (props.estado === 'conectado') return `En vivo${props.sincronizadoEn ? ` · consulta ${props.sincronizadoEn}` : ''}`
  if (props.estado === 'reconectando') return 'Reconectando · consulta manual disponible'
  if (props.estado === 'conectando') return 'Conectando · consulta manual disponible'
  return 'Sin conexión en vivo · actualiza antes de elegir un horario'
})
</script>

<template>
  <div class="realtime-row">
    <p class="realtime-status" :data-state="estado" role="status" aria-live="polite" aria-atomic="true">
      <Radio aria-hidden="true" />
      <span>{{ mensaje }}</span>
    </p>
    <BotonBase variante="secundario" tamano="pequeno" :cargando="cargando" @click="$emit('actualizar')">
      <template #icono-inicio><RefreshCw aria-hidden="true" /></template>
      {{ cargando ? 'Actualizando…' : 'Actualizar' }}
    </BotonBase>
  </div>
</template>

<style scoped>
.realtime-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 12px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface); padding: 8px 10px; }
.realtime-status { display: flex; min-width: 0; align-items: center; gap: 8px; margin: 0; color: var(--text-muted); font-size: 13px; font-weight: 600; }
.realtime-status svg { width: 16px; height: 16px; flex: 0 0 auto; }
.realtime-status[data-state='conectado'] { color: var(--status-success-text); }
.realtime-status[data-state='conectado'] svg { fill: var(--status-success-bg); }
.realtime-status[data-state='reconectando'], .realtime-status[data-state='desconectado'] { color: var(--status-warning-text); }
@media (max-width: 520px) { .realtime-row { align-items: flex-start; } }
</style>
