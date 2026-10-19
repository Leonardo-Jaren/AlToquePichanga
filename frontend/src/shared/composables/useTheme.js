import { useThemeStore } from '@/stores/theme'

export function useTheme() {
  const themeStore = useThemeStore()
  return {
    themePreference: themeStore.themePreference,
    resolvedTheme: themeStore.resolvedTheme,
    setTheme: themeStore.setTheme,
    initTheme: themeStore.initTheme,
  }
}
