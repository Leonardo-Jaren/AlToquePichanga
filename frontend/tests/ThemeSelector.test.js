import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ThemeSelector from '@/shared/components/ThemeSelector.vue'
import { useThemeStore } from '@/stores/theme'

describe('ThemeSelector Component', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    document.documentElement.className = ''
  })

  it('renderiza las 3 opciones de tema: Claro, Oscuro y Sistema', () => {
    const wrapper = mount(ThemeSelector)
    const buttons = wrapper.findAll('button')

    expect(buttons).toHaveLength(3)
    expect(wrapper.text()).toContain('Claro')
    expect(wrapper.text()).toContain('Oscuro')
    expect(wrapper.text()).toContain('Sistema')
  })

  it('cambia el tema a oscuro al presionar el botón Oscuro', async () => {
    const wrapper = mount(ThemeSelector)
    const themeStore = useThemeStore()

    const darkBtn = wrapper.find('button[data-theme-option="dark"]')
    expect(darkBtn.exists()).toBe(true)

    await darkBtn.trigger('click')

    expect(themeStore.themePreference).toBe('dark')
    expect(themeStore.resolvedTheme).toBe('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(localStorage.getItem('altoque-theme')).toBe('dark')
  })

  it('cambia el tema a claro al presionar el botón Claro', async () => {
    const wrapper = mount(ThemeSelector)
    const themeStore = useThemeStore()

    // Establecer oscuro primero
    themeStore.setTheme('dark')
    expect(document.documentElement.classList.contains('dark')).toBe(true)

    const lightBtn = wrapper.find('button[data-theme-option="light"]')
    await lightBtn.trigger('click')

    expect(themeStore.themePreference).toBe('light')
    expect(themeStore.resolvedTheme).toBe('light')
    expect(document.documentElement.classList.contains('light')).toBe(true)
    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })
})
