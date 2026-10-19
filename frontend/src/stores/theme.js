import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const themePreference = ref(localStorage.getItem('altoque-theme') || 'system')
  const systemPrefersDark = ref(
    typeof window !== 'undefined' &&
    window.matchMedia &&
    window.matchMedia('(prefers-color-scheme: dark)').matches
  )

  const resolvedTheme = computed(() => {
    if (themePreference.value === 'system') {
      return systemPrefersDark.value ? 'dark' : 'light'
    }
    return themePreference.value
  })

  function applyTheme() {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.dataset.theme = resolvedTheme.value
    if (resolvedTheme.value === 'dark') {
      root.classList.add('dark')
      root.classList.remove('light')
    } else {
      root.classList.remove('dark')
      root.classList.add('light')
    }
  }

  function setTheme(theme) {
    if (!['light', 'dark', 'system'].includes(theme)) return
    themePreference.value = theme
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('altoque-theme', theme)
    }
    applyTheme()
  }

  function initTheme() {
    if (typeof window !== 'undefined' && window.matchMedia) {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addEventListener('change', (e) => {
        systemPrefersDark.value = e.matches
        if (themePreference.value === 'system') {
          applyTheme()
        }
      })
    }
    applyTheme()
  }

  return {
    themePreference,
    resolvedTheme,
    setTheme,
    initTheme,
    applyTheme,
  }
})
