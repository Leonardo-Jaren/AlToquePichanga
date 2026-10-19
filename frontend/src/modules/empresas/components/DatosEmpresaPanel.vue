<script setup>
import { reactive, ref, watch } from 'vue'
import { empresasApi } from '../services/empresas'

const props = defineProps({ empresa: { type: Object, required: true } })
const emit = defineEmits(['guardada'])
const datos = reactive({})
const logo = ref(null)
const cargando = ref(false)
const mensaje = ref('')
const error = ref('')
const campoErrores = ref({})

watch(() => props.empresa, (empresa) => {
  Object.assign(datos, {
    razon_social: empresa.razon_social || '',
    nombre_comercial: empresa.nombre_comercial || '',
    ruc: empresa.ruc || '',
    descripcion: empresa.descripcion || '',
    correo_contacto: empresa.correo_contacto || '',
    telefono_contacto: empresa.telefono_contacto || '',
    direccion_administrativa: empresa.direccion_administrativa || '',
  })
}, { immediate: true })

function elegirLogo(evento) { logo.value = evento.target.files?.[0] || null }

async function guardar() {
  cargando.value = true
  mensaje.value = ''
  error.value = ''
  campoErrores.value = {}
  try {
    let resultado = (await empresasApi.actualizar(props.empresa.id, datos)).data
    if (logo.value) {
      resultado = { ...resultado, ...(await empresasApi.actualizarLogo(props.empresa.id, logo.value)).data }
      logo.value = null
    }
    mensaje.value = 'Datos de la empresa guardados.'
    emit('guardada', resultado)
  } catch (fallo) {
    campoErrores.value = fallo.response?.data || {}
    error.value = fallo.response?.data?.detail || 'Revisa los campos y vuelve a guardar.'
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <section class="admin-card" aria-labelledby="datos-empresa-titulo">
    <div class="mb-6">
      <h2 id="datos-empresa-titulo" class="text-xl font-bold">Datos de la empresa</h2>
      <p class="mt-1 text-sm text-app-text-muted">La información de aprobación la administra la plataforma.</p>
    </div>
    <form class="grid gap-5 md:grid-cols-2" novalidate :aria-busy="cargando" @submit.prevent="guardar">
      <label class="block">
        <span class="admin-label">Razón social</span>
        <input id="razon_social" v-model.trim="datos.razon_social" class="admin-field" maxlength="180" autocomplete="organization">
        <span v-if="campoErrores.razon_social" class="text-sm text-[var(--status-danger-text)]">{{ campoErrores.razon_social[0] }}</span>
      </label>
      <label class="block">
        <span class="admin-label">Nombre comercial</span>
        <input id="nombre_comercial" v-model.trim="datos.nombre_comercial" class="admin-field" maxlength="160">
        <span v-if="campoErrores.nombre_comercial" class="text-sm text-[var(--status-danger-text)]">{{ campoErrores.nombre_comercial[0] }}</span>
      </label>
      <label class="block">
        <span class="admin-label">RUC <span class="font-normal text-app-text-muted">(opcional, 11 dígitos)</span></span>
        <input id="ruc" v-model.trim="datos.ruc" class="admin-field" inputmode="numeric" autocomplete="off" maxlength="11">
        <span v-if="campoErrores.ruc" class="text-sm text-[var(--status-danger-text)]">{{ campoErrores.ruc[0] }}</span>
      </label>
      <label class="block">
        <span class="admin-label">Correo de contacto</span>
        <input id="correo_contacto" v-model.trim="datos.correo_contacto" class="admin-field" type="email" autocomplete="email">
        <span v-if="campoErrores.correo_contacto" class="text-sm text-[var(--status-danger-text)]">{{ campoErrores.correo_contacto[0] }}</span>
      </label>
      <label class="block">
        <span class="admin-label">Teléfono de contacto</span>
        <input id="telefono_contacto" v-model.trim="datos.telefono_contacto" class="admin-field" type="tel" autocomplete="tel">
      </label>
      <label class="block">
        <span class="admin-label">Dirección administrativa</span>
        <input id="direccion_administrativa" v-model.trim="datos.direccion_administrativa" class="admin-field" autocomplete="street-address">
      </label>
      <label class="block md:col-span-2">
        <span class="admin-label">Descripción</span>
        <textarea id="descripcion" v-model.trim="datos.descripcion" class="admin-field min-h-28" maxlength="4000" rows="4" />
      </label>
      <label class="block md:col-span-2">
        <span class="admin-label">Logotipo <span class="font-normal text-app-text-muted">(PNG, JPG o WebP; máximo 5 MB)</span></span>
        <input id="logotipo" class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" @change="elegirLogo">
      </label>
      <div class="flex flex-wrap items-center gap-3 md:col-span-2">
        <button class="admin-button admin-button-primary" :disabled="cargando">{{ cargando ? 'Guardando…' : 'Guardar cambios' }}</button>
        <p v-if="mensaje" role="status" class="text-sm text-[var(--status-success-text)]">{{ mensaje }}</p>
      </div>
      <p v-if="error" role="alert" class="admin-error md:col-span-2">{{ error }}</p>
    </form>
  </section>
</template>
