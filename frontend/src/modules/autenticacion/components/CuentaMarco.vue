<script setup>
import ThemeSelector from '@/shared/components/ThemeSelector.vue'
defineProps({ titulo: { type: String, required: true }, descripcion: { type: String, default: '' } })
</script>

<template>
  <div class="min-h-screen bg-app-bg text-app-text">
    <header class="border-b border-app-border bg-app-nav-bg">
      <div class="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 sm:px-8">
        <RouterLink to="/" class="text-sm font-semibold text-app-link">Volver al inicio</RouterLink>
        <ThemeSelector />
      </div>
    </header>
    <main class="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-8 sm:py-12 lg:grid-cols-2 lg:gap-16">
      <aside class="relative hidden overflow-hidden rounded-3xl bg-app-hero-bg p-8 text-app-hero-text sm:p-12 lg:block">
        <p class="mb-8 text-sm font-semibold tracking-wide text-brand-lime">Tu pichanga, al toque.</p>
        <h2 class="font-display max-w-md text-3xl leading-tight sm:text-5xl">El equipo empieza contigo.</h2>
        <p class="mt-6 max-w-sm text-base leading-relaxed opacity-80">Una cuenta para encontrar tu próxima cancha y llevar tu juego a otro nivel.</p>
        <div aria-hidden="true" class="relative mt-12 hidden h-40 rounded-xl border border-current opacity-20 lg:block">
          <div class="absolute inset-y-0 left-1/2 border-l border-current" />
          <div class="absolute left-1/2 top-1/2 h-20 w-20 -translate-x-1/2 -translate-y-1/2 rounded-full border border-current" />
          <div class="absolute inset-y-8 left-0 w-12 border border-l-0 border-current" />
          <div class="absolute inset-y-8 right-0 w-12 border border-r-0 border-current" />
        </div>
      </aside>
      <section class="account-card self-start" aria-labelledby="cuenta-titulo">
        <p class="mb-6 text-sm font-semibold text-app-link lg:hidden">Tu pichanga, al toque.</p>
        <h1 id="cuenta-titulo" class="font-display text-3xl leading-tight sm:text-4xl">{{ titulo }}</h1>
        <p v-if="descripcion" class="mt-3 text-app-text-muted">{{ descripcion }}</p>
        <div class="mt-8"><slot /></div>
      </section>
    </main>
  </div>
</template>
