<script setup>
defineProps({
  modelValue: { type: String, default: '' }, nombre: { type: String, required: true },
  etiqueta: { type: String, required: true }, tipo: { type: String, default: 'text' },
  autocomplete: { type: String, default: '' }, error: { type: String, default: '' },
  ayuda: { type: String, default: '' }, maximo: { type: Number, default: 150 },
})
defineEmits(['update:modelValue'])
</script>

<template>
  <div>
    <label :for="nombre" class="mb-2 block text-sm font-semibold">{{ etiqueta }}</label>
    <input :id="nombre" :name="nombre" :type="tipo" :value="modelValue" :autocomplete="autocomplete"
      :maxlength="maximo" class="account-input" :aria-invalid="error ? 'true' : undefined"
      :aria-describedby="error || ayuda ? `${nombre}-ayuda` : undefined"
      @input="$emit('update:modelValue', $event.target.value)">
    <p v-if="error || ayuda" :id="`${nombre}-ayuda`" class="mt-2 text-sm"
      :class="error ? 'text-[var(--status-danger-text)]' : 'text-app-text-muted'">{{ error || ayuda }}</p>
  </div>
</template>
