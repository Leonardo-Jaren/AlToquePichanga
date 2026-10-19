<script setup>
import CuentaMarco from '../components/CuentaMarco.vue'
import CampoFormulario from '@/shared/components/CampoFormulario.vue'
import { useFormulario } from '../composables/useFormulario'
import { cuenta } from '../services/cuenta'
import { ref } from 'vue'
const confirmado = ref(false)
const { datos, errores, mensaje, ocupado, ejecutar } = useFormulario({ correo: '' })
async function recuperar() { confirmado.value = await ejecutar(() => cuenta.recuperar(datos)) }
</script>

<template>
  <CuentaMarco titulo="Recupera tu acceso" descripcion="Te enviaremos un enlace para elegir una nueva contraseña.">
    <p v-if="confirmado" role="status" class="account-success">Si el correo corresponde a una cuenta, recibirás un enlace. Revisa también tu carpeta de spam.</p>
    <form v-else class="space-y-5" novalidate @submit.prevent="recuperar">
      <CampoFormulario v-model="datos.correo" nombre="correo" etiqueta="Correo electrónico" tipo="email" autocomplete="email" :maximo="254" :error="errores.correo" />
      <p v-if="mensaje" role="alert" class="account-error">{{ mensaje }}</p>
      <button class="account-primary w-full" :disabled="ocupado">{{ ocupado ? 'Enviando…' : 'Enviar enlace' }}</button>
    </form>
    <RouterLink to="/ingresar" class="mt-6 inline-block text-sm text-app-link">Volver a iniciar sesión</RouterLink>
  </CuentaMarco>
</template>
