<script setup>
import { ref } from 'vue'
import { cuenta } from '../services/cuenta'
defineProps({ vincular: { type: Boolean, default: false } })
const ocupado = ref(false)
const error = ref('')
async function continuar(vincular) {
  ocupado.value = true
  error.value = ''
  try { window.location.assign((await cuenta.google(vincular)).data.url) } catch (err) {
    error.value = err.response?.data?.detail || 'Google no está disponible. Intenta con tu correo.'
    ocupado.value = false
  }
}
</script>

<template>
  <button type="button" class="account-secondary w-full" :disabled="ocupado" @click="continuar(vincular)">
    {{ ocupado ? 'Conectando…' : vincular ? 'Vincular mi cuenta de Google' : 'Continuar con Google' }}
  </button>
  <p v-if="error" role="alert" class="mt-3 text-sm text-[var(--status-danger-text)]">{{ error }}</p>
</template>
