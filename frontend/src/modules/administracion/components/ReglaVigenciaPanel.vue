<script setup>
import { onMounted, reactive, ref } from 'vue'
import { plataformaApi } from '@/modules/empresas/services/empresas'

const cargando = ref(false)
const guardando = ref(false)
const error = ref('')
const mensaje = ref('')
const form = reactive({ dias_gracia: 0 })

onMounted(cargar)
async function cargar() {
  cargando.value = true
  error.value = ''
  try { Object.assign(form, (await plataformaApi.configuracion()).data) }
  catch (fallo) { error.value = fallo.response?.data?.detail || 'No se pudo cargar la vigencia configurada.' }
  finally { cargando.value = false }
}
async function guardar() {
  guardando.value = true
  error.value = ''
  mensaje.value = ''
  try {
    const { data } = await plataformaApi.guardarConfiguracion({ dias_gracia: Number(form.dias_gracia) })
    form.dias_gracia = data.dias_gracia
    mensaje.value = 'La vigencia configurada fue guardada.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo guardar la vigencia.'
  } finally { guardando.value = false }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="vigencia-titulo">
    <div>
      <h2 id="vigencia-titulo" class="text-xl font-bold">Regla central de vencimiento</h2>
      <p class="mt-1 max-w-3xl text-sm text-app-text-muted">Los días de gracia se aplican después de la fecha de vencimiento, según la fecha local de Perú. La configuración también se registra en auditoría.</p>
    </div>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>
    <form class="admin-card max-w-xl space-y-4" @submit.prevent="guardar" :aria-busy="cargando || guardando">
      <label class="block">
        <span class="admin-label">Días de gracia</span>
        <input v-model.number="form.dias_gracia" class="admin-field" type="number" min="0" step="1" required>
        <span class="mt-2 block text-sm text-app-text-muted">Con 0 días, las funciones con acceso comercial se restringen al día siguiente del vencimiento.</span>
      </label>
      <button class="admin-button admin-button-primary" :disabled="cargando || guardando">
        {{ guardando ? 'Guardando…' : 'Guardar regla' }}
      </button>
    </form>
  </section>
</template>
