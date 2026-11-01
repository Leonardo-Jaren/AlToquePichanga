<script setup>
import { ref, watch } from 'vue'
import BotonBase from '@/shared/components/BotonBase.vue'
import { pagosApi } from '../services/pagos'

const props = defineProps({ sedeId: { type: [String, Number], default: '' } })
const texto = ref('')
const version = ref(null)
const error = ref('')
const aviso = ref('')
const cargando = ref(false)
watch(() => props.sedeId, async (id) => {
  texto.value = ''; version.value = null; error.value = ''; aviso.value = ''
  if (!id) return
  try {
    const { data } = await pagosApi.obtenerCondiciones(id)
    if (String(props.sedeId) !== String(id)) return
    texto.value = data?.texto || ''; version.value = data?.version || null
  } catch { if (String(props.sedeId) === String(id)) error.value = 'No se pudieron consultar las condiciones de la sede.' }
}, { immediate: true })
async function guardar() {
  if (!texto.value.trim()) { error.value = 'Escribe las condiciones antes de guardarlas.'; return }
  cargando.value = true; error.value = ''; aviso.value = ''
  const sedeGuardada = props.sedeId
  try {
    const { data } = await pagosApi.guardarCondiciones(sedeGuardada, { texto: texto.value.trim() })
    if (String(props.sedeId) !== String(sedeGuardada)) return
    version.value = data.version; texto.value = data.texto
    aviso.value = `Condiciones guardadas · versión ${data.version}.`
  } catch { if (String(props.sedeId) === String(sedeGuardada)) error.value = 'No se pudieron guardar las condiciones.' }
  finally { cargando.value = false }
}
</script>

<template>
  <section class="condiciones" aria-labelledby="condiciones-sede-titulo">
    <div><h3 id="condiciones-sede-titulo">Condiciones de cancelación</h3><p>El jugador debe leer y aceptar la versión vigente antes de iniciar el pago. Revisa el contenido legal antes de usarlo con clientes.</p></div>
    <template v-if="sedeId">
      <p v-if="version" class="condiciones-version">Versión vigente: {{ version }}</p>
      <label for="condiciones-sede">Texto de la sede</label>
      <textarea id="condiciones-sede" v-model="texto" maxlength="6000" rows="5" />
      <p v-if="error" role="alert">{{ error }}</p><p v-if="aviso" role="status">{{ aviso }}</p>
      <BotonBase variante="primario" :cargando="cargando" @click="guardar">Guardar condiciones</BotonBase>
    </template>
    <p v-else>Elige una sede para configurar sus condiciones.</p>
  </section>
</template>

<style scoped>
.condiciones { display: grid; gap: 10px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 18px; }
.condiciones h3, .condiciones p { margin: 0; }
.condiciones p { color: var(--text-muted); font-size: 14px; }
.condiciones label { font-weight: 600; }
.condiciones textarea { width: 100%; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); color: var(--text); padding: 12px; }
.condiciones-version { font-weight: 700; }
.condiciones :deep(.boton-base) { justify-self: start; }
</style>
