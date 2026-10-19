<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import ThemeSelector from '@/shared/components/ThemeSelector.vue'
import { useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'

defineProps({
  titulo: { type: String, required: true },
  descripcion: { type: String, default: '' },
  secciones: { type: Array, default: () => [] },
  activa: { type: String, default: '' },
})
const emit = defineEmits(['cambiar-seccion'])
const auth = useAutenticacionStore()
const router = useRouter()
const menuMovil = ref(false)
const errorSesion = ref('')

async function salir() {
  errorSesion.value = ''
  try {
    await auth.salir()
    await router.replace('/ingresar')
  } catch {
    errorSesion.value = 'No se pudo cerrar la sesión. Inténtalo de nuevo.'
  }
}
</script>

<template>
  <div class="admin-frame min-h-screen bg-app-bg text-app-text">
    <header class="admin-topbar">
      <div class="mx-auto flex min-h-[68px] max-w-7xl items-center justify-between gap-4 px-4 sm:px-8">
        <RouterLink to="/" class="admin-brand-link">
          <img class="admin-logo admin-logo-light" src="/logos/logo_completo_negro.png" alt="AlToque Pichanga">
          <img class="admin-logo admin-logo-dark" src="/logos/logo_completo.png" alt="AlToque Pichanga">
          <span class="text-sm text-app-text-muted sm:text-base">/ Administración</span>
        </RouterLink>
        <div class="flex items-center gap-3">
          <ThemeSelector />
          <span class="hidden max-w-48 truncate text-sm text-app-text-muted sm:block">{{ auth.usuario?.nombre }}</span>
          <button class="admin-button admin-button-quiet" type="button" @click="salir">Cerrar sesión</button>
        </div>
      </div>
    </header>

    <div class="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-[230px_minmax(0,1fr)] lg:gap-8 lg:py-8">
      <aside class="admin-sidebar">
        <div v-if="secciones.length" class="mb-4 flex items-center justify-between lg:hidden">
          <span class="text-sm font-semibold">Secciones</span>
          <button class="admin-button admin-button-quiet" type="button" :aria-expanded="menuMovil" @click="menuMovil = !menuMovil">
            {{ menuMovil ? 'Ocultar' : 'Mostrar' }}
          </button>
        </div>
        <nav v-if="secciones.length" :class="['admin-nav', menuMovil ? 'admin-nav-open' : '']" aria-label="Administración">
          <button v-for="seccion in secciones" :key="seccion.id" type="button"
            :class="['admin-nav-link', activa === seccion.id ? 'admin-nav-link-active' : '']"
            :aria-current="activa === seccion.id ? 'page' : undefined"
            @click="emit('cambiar-seccion', seccion.id); menuMovil = false">
            <span>{{ seccion.nombre }}</span>
            <span v-if="activa === seccion.id" class="admin-nav-line" aria-hidden="true" />
          </button>
        </nav>
        <slot name="sidebar" />
        <p class="mt-6 hidden border-t border-app-border pt-4 text-xs text-app-text-subtle lg:block">Tu pichanga, al toque.</p>
      </aside>

      <main class="min-w-0">
        <section class="admin-page-heading" aria-labelledby="admin-titulo">
          <div class="admin-field-mark" aria-hidden="true" />
          <div>
            <h1 id="admin-titulo" class="font-display text-2xl leading-tight sm:text-3xl">{{ titulo }}</h1>
            <p v-if="descripcion" class="mt-2 max-w-3xl text-sm text-app-text-muted sm:text-base">{{ descripcion }}</p>
          </div>
        </section>
        <p v-if="errorSesion" role="alert" class="admin-error mb-4">{{ errorSesion }}</p>
        <slot />
      </main>
    </div>
  </div>
</template>

<style>
@import '../admin.css';
</style>
