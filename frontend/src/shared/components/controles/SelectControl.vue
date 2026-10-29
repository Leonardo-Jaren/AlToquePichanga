<script setup>
import { computed } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

defineOptions({ inheritAttrs: false })
const props = defineProps({
  id: { type: String, required: true },
  label: { type: String, default: '' },
  modelValue: { type: [String, Number], default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '' },
  error: { type: String, default: '' },
  hint: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  required: { type: Boolean, default: false },
  wrapperClass: { type: String, default: '' },
  variant: { type: String, default: 'admin' },
})
const emit = defineEmits(['update:modelValue'])
const describedBy = computed(() => [props.hint && `${props.id}-hint`, props.error && `${props.id}-error`].filter(Boolean).join(' ') || undefined)
</script>

<template>
  <label class="block min-w-0" :class="wrapperClass" :for="id">
    <span v-if="label" :class="variant === 'public' ? 'mb-1 block text-sm font-semibold text-[var(--text)]' : 'admin-label'">{{ label }}<span v-if="required" aria-hidden="true"> *</span></span>
    <span class="relative block">
      <select
        v-bind="$attrs"
        :id="id"
        :value="modelValue"
        :disabled="disabled"
        :required="required"
        :aria-invalid="error ? 'true' : undefined"
        :aria-describedby="describedBy"
        :class="variant === 'public'
          ? 'min-h-11 w-full rounded-xl border border-[var(--border-strong)] bg-[var(--input-bg)] px-3 py-2 pr-10 text-[var(--text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--brand-lime)]'
          : 'admin-field appearance-none pr-10'"
        @change="emit('update:modelValue', $event.target.value)"
      >
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option v-for="option in options" :key="String(option.value)" :value="option.value">{{ option.label }}</option>
      </select>
      <ChevronDown aria-hidden="true" class="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-[var(--text-muted)]" />
    </span>
    <span v-if="hint" :id="`${id}-hint`" class="mt-1 block text-xs text-[var(--text-muted)]">{{ hint }}</span>
    <span v-if="error" :id="`${id}-error`" class="mt-1 block text-xs text-[var(--status-danger-text)]" role="alert">{{ error }}</span>
  </label>
</template>
