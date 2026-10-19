<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import CuentaMarco from '../components/CuentaMarco.vue'
import { cuenta } from '../services/cuenta'
import { puedeAcceder, useAutenticacionStore } from '../stores/autenticacion'
const route = useRoute()
const auth = useAutenticacionStore()
const nombres = { plataforma: 'Plataforma', dueno: 'Dueño de empresa', administrador_sede: 'Administrador de sede', cajero: 'Cajero / Empleado', jugador: 'Jugador' }
const roles = computed(() => Object.keys(nombres).filter((rol) => puedeAcceder(auth.usuario, rol)))
const estado = ref('Verificando acceso…')
async function verificar() {
  estado.value = 'Verificando acceso…'
  try { estado.value = (await cuenta.panel(route.meta.rol)).data.mensaje }
  catch { estado.value = 'No se pudo autorizar el acceso. Vuelve a iniciar sesión.' }
}
onMounted(verificar)
watch(() => route.meta.rol, verificar)
</script>

<template>
  <CuentaMarco :titulo="`Espacio de ${nombres[route.meta.rol]}`" descripcion="Tu acceso, en un solo lugar.">
    <p role="status" class="text-app-text-muted">{{ estado }}</p>
    <nav class="mt-6 flex flex-wrap gap-3" aria-label="Espacios autorizados">
      <RouterLink v-for="rol in roles" :key="rol" :to="`/panel/${rol}`" class="account-secondary" :aria-current="rol === route.meta.rol ? 'page' : undefined">{{ nombres[rol] }}</RouterLink>
    </nav>
    <RouterLink to="/perfil" class="mt-8 inline-block font-semibold text-app-link">Mi perfil y sesión</RouterLink>
  </CuentaMarco>
</template>
