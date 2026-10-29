<script setup>
import { reactive, ref, watch } from 'vue'
import { BadgeCheck, ImagePlus, Save } from 'lucide-vue-next'
import BotonBase from '@/shared/components/BotonBase.vue'
import { pagosApi } from '../services/pagos'

const props = defineProps({
  sedeId: { type: Number, required: true },
  tipo: { type: String, required: true },
  metodo: { type: Object, default: null },
})
const emit = defineEmits(['guardado'])
const datos = reactive({ titular: '', numero_cuenta: '', banco: '', cci: '', instrucciones: '', activo: true })
const qr = ref(null)
const guardando = ref(false)
const error = ref('')
const ok = ref(false)

watch(() => props.metodo, cargar, { immediate: true })
function cargar(metodo) {
  Object.assign(datos, {
    titular: metodo?.titular || '', numero_cuenta: metodo?.numero_cuenta || '',
    banco: metodo?.banco || '', cci: metodo?.cci || '',
    instrucciones: metodo?.instrucciones || '', activo: metodo?.activo ?? true,
  })
  qr.value = null
}

async function guardar() {
  if (guardando.value) return
  guardando.value = true
  error.value = ''
  ok.value = false
  try {
    const formulario = new FormData()
    Object.entries({ tipo: props.tipo, ...datos }).forEach(([campo, valor]) => formulario.append(campo, String(valor)))
    if (qr.value) formulario.append('imagen_qr', qr.value)
    await pagosApi.guardarMedio(props.sedeId, formulario)
    ok.value = true
    emit('guardado')
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo guardar este medio de pago.'
  } finally { guardando.value = false }
}
</script>

<template>
  <form class="metodo-form" @submit.prevent="guardar" :aria-busy="guardando">
    <div class="metodo-form-titulo">
      <div><h3>{{ tipo === 'transferencia' ? 'Transferencia bancaria' : tipo.toUpperCase() }}</h3><p>{{ metodo ? 'Edita los datos que verá el jugador.' : 'Agrega los datos que verá el jugador.' }}</p></div>
      <span :class="['metodo-activo', datos.activo ? 'activo' : 'inactivo']">{{ datos.activo ? 'Visible' : 'Pausado' }}</span>
    </div>
    <label><span class="admin-label">Titular de la cuenta *</span><input v-model.trim="datos.titular" class="admin-field" required maxlength="160" autocomplete="off"></label>
    <div class="grid gap-3 sm:grid-cols-2">
      <label><span class="admin-label">{{ tipo === 'transferencia' ? 'Número de cuenta' : 'Celular asociado' }}{{ tipo === 'transferencia' ? '' : ' *' }}</span><input v-model.trim="datos.numero_cuenta" class="admin-field" :required="tipo !== 'transferencia'" maxlength="40" inputmode="numeric" autocomplete="off"></label>
      <label v-if="tipo === 'transferencia'"><span class="admin-label">Banco *</span><input v-model.trim="datos.banco" class="admin-field" required maxlength="100"></label>
    </div>
    <label v-if="tipo === 'transferencia'"><span class="admin-label">CCI (opcional)</span><input v-model.trim="datos.cci" class="admin-field" maxlength="24" inputmode="numeric" autocomplete="off"></label>
    <label><span class="admin-label">Instrucción corta</span><textarea v-model.trim="datos.instrucciones" class="admin-field min-h-16" maxlength="240" rows="2" placeholder="Ej.: coloca el código de reserva en el concepto." /></label>
    <label class="qr-subida"><span><ImagePlus aria-hidden="true" class="size-4" /> QR de pago <small>(PNG, JPG o WebP; máx. 5 MB)</small></span><input class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" @change="qr = $event.target.files?.[0] || null"></label>
    <label class="check-activo"><input v-model="datos.activo" type="checkbox"><span>Mostrar este medio de pago a los jugadores</span></label>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="ok" role="status" class="admin-success"><BadgeCheck aria-hidden="true" class="size-4" />Cambios guardados.</p>
    <BotonBase tipo="submit" variante="primario" :cargando="guardando" :deshabilitado="!datos.titular.trim()"><template #icono-inicio><Save aria-hidden="true" /></template>{{ guardando ? 'Guardando…' : 'Guardar medio' }}</BotonBase>
  </form>
</template>

<style scoped>
.metodo-form { display: grid; gap: 12px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 17px; }
.metodo-form-titulo { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.metodo-form-titulo h3 { margin: 0; font-size: 16px; }
.metodo-form-titulo p { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; }
.metodo-activo { border-radius: 999px; padding: 5px 8px; font-size: 10px; font-weight: 700; }
.metodo-activo.activo { background: var(--success-bg); color: var(--success); }
.metodo-activo.inactivo { background: var(--surface-2); color: var(--text-muted); }
.qr-subida > span { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-bottom: 4px; font-size: 12px; font-weight: 600; }
.qr-subida > span svg { color: var(--link); }
.qr-subida small { color: var(--text-muted); font-size: 10px; font-weight: 400; }
.check-activo { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.check-activo input { width: 17px; height: 17px; accent-color: var(--brand-lime-hover); }
.admin-label { display: block; margin-bottom: 5px; color: var(--text); font-size: 12px; font-weight: 600; }
.admin-field { width: 100%; min-height: 44px; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); padding: 9px 11px; color: var(--text); font: 13px var(--font-body); }
.admin-field:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.admin-error,.admin-success { display: flex; align-items: center; gap: 6px; margin: 0; border-radius: var(--radius-sm); padding: 9px; font-size: 12px; }
.admin-error { background: var(--danger-bg); color: var(--danger); }
.admin-success { background: var(--success-bg); color: var(--success); }
</style>
