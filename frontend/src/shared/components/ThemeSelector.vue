<script setup>
import { computed } from 'vue'
import { Sun, Moon, Monitor } from 'lucide-vue-next'
import { useThemeStore } from '@/stores/theme'

const themeStore = useThemeStore()

const currentTheme = computed(() => themeStore.themePreference)

const options = [
  { value: 'light', label: 'Claro', icon: Sun },
  { value: 'dark', label: 'Oscuro', icon: Moon },
  { value: 'system', label: 'Sistema', icon: Monitor },
]

function selectTheme(val) {
  themeStore.setTheme(val)
}

function mover(event, posicion) {
  const desplazamiento = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[event.key]
  if (!desplazamiento) return
  event.preventDefault()
  const siguiente = (posicion + desplazamiento + options.length) % options.length
  selectTheme(options[siguiente].value)
  event.currentTarget.parentElement.querySelectorAll('button')[siguiente].focus()
}
</script>

<template>
  <div
    class="inline-flex items-center p-1 rounded-xl border border-[var(--border)] bg-[var(--surface-2)] shadow-sm"
    role="radiogroup"
    aria-label="Selector de tema"
  >
    <button
      v-for="(opt, posicion) in options"
      :key="opt.value"
      type="button"
      :data-theme-option="opt.value"
      :class="[
        'flex min-h-11 items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 cursor-pointer select-none',
        currentTheme === opt.value
          ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs font-semibold ring-1 ring-[var(--brand-lime)]'
          : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-3)]',
      ]"
      :aria-checked="currentTheme === opt.value"
      role="radio"
      @click="selectTheme(opt.value)"
      @keydown="mover($event, posicion)"
    >
      <component :is="opt.icon" aria-hidden="true" class="w-3.5 h-3.5" />
      <span>{{ opt.label }}</span>
    </button>
  </div>
</template>
