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
const invitacionToken = ref(new URLSearchParams(window.location.hash.slice(1)).get('invitacion') || '')
const { datos, errores, mensaje, ocupado, ejecutar } = useFormulario({
  nombre: '', apellidos: '', correo: '', contrasena: '', confirmacion: '',
})
async function registrar() {
  const { confirmacion, ...registro } = datos
  if (invitacionToken.value) registro.invitacion = invitacionToken.value
  if (await ejecutar(() => auth.registrar(registro))) {
    await router.replace(invitacionToken.value ? destinoUsuario(auth.usuario) : '/perfil')
  }
}
</script>

<template>
  <CuentaMarco :titulo="invitacionToken ? 'Acepta tu invitación' : 'Súmate al juego'" :descripcion="invitacionToken ? 'Crea tu cuenta para acceder a tu empresa.' : 'Crea tu cuenta de jugador.'">
    <form class="space-y-5" novalidate :aria-busy="ocupado" @submit.prevent="registrar">
      <div class="grid gap-5 sm:grid-cols-2">
        <CampoFormulario v-model="datos.nombre" nombre="nombre" etiqueta="Nombre" autocomplete="given-name" :error="errores.nombre" />
        <CampoFormulario v-model="datos.apellidos" nombre="apellidos" etiqueta="Apellidos (opcional)" autocomplete="family-name" :error="errores.apellidos" />
      </div>
      <CampoFormulario v-model="datos.correo" nombre="correo" etiqueta="Correo electrónico" tipo="email" autocomplete="email" :maximo="254" :error="errores.correo" />
      <CampoFormulario v-model="datos.contrasena" nombre="contrasena" etiqueta="Contraseña" tipo="password" autocomplete="new-password" :maximo="128" :error="errores.contrasena" ayuda="Usa al menos 8 caracteres; evita claves comunes o similares a tus datos." />
      <CampoFormulario v-model="datos.confirmacion" nombre="confirmacion" etiqueta="Repite la contraseña" tipo="password" autocomplete="new-password" :maximo="128" :error="errores.confirmacion" />
      <p v-if="mensaje" role="alert" class="account-error">{{ mensaje }}</p>
      <button class="account-primary w-full" :disabled="ocupado">{{ ocupado ? 'Creando cuenta…' : 'Crear mi cuenta' }}</button>
    </form>
    <div class="my-6 border-t border-app-border" /><GoogleBoton />
    <p class="mt-6 text-sm text-app-text-muted">¿Ya tienes cuenta? <RouterLink to="/ingresar" class="font-semibold text-app-link">Inicia sesión</RouterLink></p>
  </CuentaMarco>
</template>
