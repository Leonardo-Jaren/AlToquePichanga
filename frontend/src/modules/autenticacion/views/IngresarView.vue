<script setup>
import { useRouter } from 'vue-router'
import CuentaMarco from '../components/CuentaMarco.vue'
import GoogleBoton from '../components/GoogleBoton.vue'
import CampoFormulario from '@/shared/components/CampoFormulario.vue'
import { useFormulario } from '../composables/useFormulario'
import { destinoUsuario, useAutenticacionStore } from '../stores/autenticacion'
const router = useRouter()
const auth = useAutenticacionStore()
const { datos, errores, mensaje, ocupado, ejecutar } = useFormulario({ correo: '', contrasena: '' })
async function ingresar() {
  if (await ejecutar(() => auth.ingresar(datos))) await router.replace(destinoUsuario(auth.usuario))
}
</script>

<template>
  <CuentaMarco titulo="Vuelve a la cancha" descripcion="Ingresa para acceder a tu cuenta.">
    <form class="space-y-5" novalidate :aria-busy="ocupado" @submit.prevent="ingresar">
      <CampoFormulario v-model="datos.correo" nombre="correo" etiqueta="Correo electrónico" tipo="email"
        autocomplete="email" :maximo="254" :error="errores.correo" />
      <CampoFormulario v-model="datos.contrasena" nombre="contrasena" etiqueta="Contraseña" tipo="password"
        autocomplete="current-password" :maximo="128" :error="errores.contrasena" />
      <RouterLink to="/recuperar" class="inline-block text-sm text-app-link">Olvidé mi contraseña</RouterLink>
      <p v-if="mensaje" role="alert" class="account-error">{{ mensaje }}</p>
      <button class="account-primary w-full" :disabled="ocupado">{{ ocupado ? 'Ingresando…' : 'Iniciar sesión' }}</button>
    </form>
    <div class="my-6 border-t border-app-border" />
    <GoogleBoton />
    <p class="mt-6 text-sm text-app-text-muted">¿Primera pichanga aquí? <RouterLink to="/registro" class="font-semibold text-app-link">Crea tu cuenta</RouterLink></p>
  </CuentaMarco>
</template>
