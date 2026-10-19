<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import CuentaMarco from '../components/CuentaMarco.vue'
import { destinoUsuario, useAutenticacionStore } from '../stores/autenticacion'
const auth = useAutenticacionStore()
const route = useRoute()
const router = useRouter()
const mensaje = ref('Verificando tu acceso…')
onMounted(async () => {
  if (route.query.error) {
    mensaje.value = 'No se pudo completar el acceso con Google. Si ya tienes cuenta, ingresa con tu contraseña y vincula Google desde tu perfil.'
    return
  }
  try {
    await auth.recuperarSesion()
    if (auth.usuario) await router.replace(destinoUsuario(auth.usuario))
    else mensaje.value = 'No se pudo recuperar la sesión. Intenta ingresar nuevamente.'
  } catch { mensaje.value = 'No pudimos conectar. Comprueba tu conexión e intenta nuevamente.' }
})
</script>
<template>
  <CuentaMarco titulo="Acceso con Google">
    <p role="status" class="text-app-text-muted">{{ mensaje }}</p>
    <RouterLink to="/ingresar" class="mt-6 inline-block text-app-link">Volver a iniciar sesión</RouterLink>
  </CuentaMarco>
</template>
