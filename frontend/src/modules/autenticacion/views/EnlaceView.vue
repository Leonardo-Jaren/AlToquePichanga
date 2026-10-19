<script setup>
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import CuentaMarco from '../components/CuentaMarco.vue'
import CampoFormulario from '@/shared/components/CampoFormulario.vue'
import { useFormulario } from '../composables/useFormulario'
import { cuenta } from '../services/cuenta'
const route = useRoute()
const verificar = computed(() => route.name === 'verificar-correo')
const parametros = new URLSearchParams(route.hash.slice(1))
const enlace = { uid: parametros.get('uid') || '', token: parametros.get('token') || '' }
const confirmado = ref(false)
const { datos, errores, mensaje, ocupado, ejecutar } = useFormulario(
  verificar.value ? {} : { contrasena: '', confirmacion: '' },
)
async function confirmar() {
  confirmado.value = await ejecutar(() => verificar.value ? cuenta.verificar(enlace)
    : cuenta.restablecer({ ...enlace, contrasena: datos.contrasena }))
}
</script>

<template>
  <CuentaMarco :titulo="verificar ? 'Verifica tu correo' : 'Nueva contraseña'" descripcion="Completa este paso para proteger tu cuenta.">
    <p v-if="confirmado" role="status" class="account-success">{{ verificar ? 'Correo verificado.' : 'Contraseña actualizada.' }}</p>
    <form v-else class="space-y-5" novalidate @submit.prevent="confirmar">
      <template v-if="!verificar">
        <CampoFormulario v-model="datos.contrasena" nombre="contrasena" etiqueta="Nueva contraseña" tipo="password" autocomplete="new-password" :maximo="128" :error="errores.contrasena" />
        <CampoFormulario v-model="datos.confirmacion" nombre="confirmacion" etiqueta="Repite la contraseña" tipo="password" autocomplete="new-password" :maximo="128" :error="errores.confirmacion" />
      </template>
      <p v-if="mensaje" role="alert" class="account-error">{{ mensaje }}</p>
      <button class="account-primary w-full" :disabled="ocupado || !enlace.uid || !enlace.token">{{ ocupado ? 'Guardando…' : verificar ? 'Verificar correo' : 'Guardar contraseña' }}</button>
      <p v-if="!enlace.uid || !enlace.token" role="alert" class="account-error">El enlace está incompleto. Abre el enlace que recibiste por correo.</p>
    </form>
    <RouterLink to="/ingresar" class="mt-6 inline-block text-sm text-app-link">Ir a iniciar sesión</RouterLink>
  </CuentaMarco>
</template>
