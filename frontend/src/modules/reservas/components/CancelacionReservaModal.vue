<script setup>
import { ref, watch } from 'vue'
import ModalBase from '@/shared/components/ModalBase.vue'
import BotonBase from '@/shared/components/BotonBase.vue'
import { reservasApi } from '../services/reservas'

const props = defineProps({ modelValue: Boolean, codigo: { type: String, default: '' }, condiciones: { type: String, default: '' }, administrativa: Boolean })
const emit = defineEmits(['update:modelValue', 'cancelada'])
const motivo = ref('')
const error = ref('')
const cargando = ref(false)
watch(() => props.modelValue, (abierto) => { if (abierto) { motivo.value = ''; error.value = '' } })
async function confirmar() {
  if (!motivo.value.trim()) { error.value = 'Indica el motivo de la cancelación.'; return }
  cargando.value = true
  error.value = ''
  try {
    const datos = { motivo: motivo.value.trim() }
    const respuesta = props.administrativa
      ? await reservasApi.cancelarAdministracion(props.codigo, datos)
      : await reservasApi.cancelarReserva(props.codigo, datos)
    emit('cancelada', respuesta.data)
    emit('update:modelValue', false)
  } catch { error.value = 'No se pudo cancelar. Comprueba el estado y contacta a la sede si necesitas ayuda.' }
  finally { cargando.value = false }
}
</script>

<template>
  <ModalBase :model-value="modelValue" titulo="Cancelar reserva" :descripcion="codigo" @update:model-value="emit('update:modelValue', $event)">
    <div class="cancelacion">
      <p v-if="condiciones" class="texto-condiciones">{{ condiciones }}</p>
      <p>Las cancelaciones voluntarias normalmente no generan devolución del adelanto. Las excepciones y los derechos aplicables pueden requerir revisión de la sede.</p>
      <p>El horario se liberará y los pagos registrados se conservarán. No se hará ninguna devolución automática.</p>
      <label for="motivo-cancelacion">Motivo de cancelación</label>
      <textarea id="motivo-cancelacion" v-model.trim="motivo" rows="3" maxlength="240" required />
      <p v-if="error" role="alert" class="cancelacion-error">{{ error }}</p>
    </div>
    <template #pie><BotonBase @click="emit('update:modelValue', false)">Volver</BotonBase><BotonBase variante="primario" :cargando="cargando" @click="confirmar">Confirmar cancelación</BotonBase></template>
  </ModalBase>
</template>

<style scoped>
.cancelacion { display: grid; gap: 12px; }
.cancelacion p { margin: 0; color: var(--text-muted); }
.texto-condiciones { white-space: pre-wrap; }
.cancelacion label { font-weight: 600; }
.cancelacion textarea { width: 100%; min-height: 80px; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); color: var(--text); padding: 10px; }
.cancelacion .cancelacion-error { color: var(--danger); }
</style>
