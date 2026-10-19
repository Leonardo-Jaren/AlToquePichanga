<script setup>
import { useRouter } from 'vue-router'
import { ref } from 'vue'
import CuentaMarco from '../components/CuentaMarco.vue'
import GoogleBoton from '../components/GoogleBoton.vue'
import CampoFormulario from '@/shared/components/CampoFormulario.vue'
import { useFormulario } from '../composables/useFormulario'
import { destinoUsuario, useAutenticacionStore } from '../stores/autenticacion'
const auth = useAutenticacionStore()
const router = useRouter()
const guardado = ref(false)
const { datos, errores, mensaje, ocupado, ejecutar } = useFormulario({
  nombre: auth.usuario?.nombre || '', apellidos: auth.usuario?.apellidos || '',
})
async function guardar() { guardado.value = await ejecutar(() => auth.actualizar(datos)) }
async function salir() { if (await ejecutar(() => auth.salir(), false)) await router.replace('/ingresar') }
</script>

<template>
  <CuentaMarco titulo="Tu perfil" descripcion="Mantén tus datos al día.">
    <div class="mb-6 break-words text-sm text-app-text-muted">
      <p>{{ auth.usuario?.correo }}</p>
      <p>{{ auth.usuario?.correo_verificado ? 'Correo verificado' : 'Revisa tu correo para verificar tu cuenta.' }}</p>
    </div>
    <form class="space-y-5" novalidate @submit.prevent="guardar">
      <CampoFormulario v-model="datos.nombre" nombre="nombre" etiqueta="Nombre" autocomplete="given-name" :error="errores.nombre" />
      <CampoFormulario v-model="datos.apellidos" nombre="apellidos" etiqueta="Apellidos (opcional)" autocomplete="family-name" :error="errores.apellidos" />
      <p v-if="guardado" role="status" class="account-success">Cambios guardados.</p>
      <p v-if="mensaje" role="alert" class="account-error">{{ mensaje }}</p>
      <button class="account-primary w-full" :disabled="ocupado">{{ ocupado ? 'Guardando…' : 'Guardar cambios' }}</button>
    </form>
    <div class="my-6 border-t border-app-border" /><GoogleBoton vincular />
    <div class="mt-6 flex flex-wrap items-center justify-between gap-4">
      <RouterLink :to="destinoUsuario(auth.usuario)" class="text-sm font-semibold text-app-link">Ir a mi espacio</RouterLink>
      <button class="account-secondary" :disabled="ocupado" @click="salir">Cerrar sesión</button>
    </div>
  </CuentaMarco>
</template>
