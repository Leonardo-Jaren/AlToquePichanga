<script setup>
import { useRoute } from 'vue-router'
import CuentaMarco from '../components/CuentaMarco.vue'
const route = useRoute()
</script>
<template>
  <CuentaMarco :titulo="route.name === 'sin-permiso' ? 'Acceso restringido' : 'No pudimos verificar tu sesión'"
    :descripcion="route.name === 'sin-permiso' ? 'Tu cuenta no tiene permisos para abrir este espacio.' : 'Comprueba tu conexión e intenta nuevamente.'">
    <RouterLink to="/perfil" class="account-primary inline-flex items-center">Volver a mi cuenta</RouterLink>
  </CuentaMarco>
</template>
