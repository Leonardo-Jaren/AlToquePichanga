<script setup>
import { computed, onMounted, ref } from 'vue'
import { ArrowLeft, CalendarDays, MapPin, Users } from 'lucide-vue-next'
import ThemeSelector from '@/shared/components/ThemeSelector.vue'
import SelectControl from '@/shared/components/controles/SelectControl.vue'
import { canchasApi } from '@/modules/canchas/services/canchas'
import { useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'
import CalendarioOperativo from '../components/calendario/CalendarioOperativo.vue'

const canchas = ref([])
const auth = useAutenticacionStore()
const canchaId = ref('')
const cargando = ref(false)
const error = ref('')
const cancha = computed(() => canchas.value.find((item) => String(item.id) === String(canchaId.value)))
const opciones = computed(() => canchas.value.map((item) => ({
  value: String(item.id),
  label: `${item.nombre} · ${item.sede.distrito || item.sede.nombre}`,
})))
const ubicacion = computed(() => cancha.value
  ? [cancha.value.sede?.distrito, cancha.value.sede?.provincia, cancha.value.sede?.departamento].filter(Boolean).join(', ')
  : '')

onMounted(async () => {
  try { await auth.recuperarSesion() } catch { /* La consulta pública continúa sin sesión. */ }
  await cargarCanchas()
})

async function cargarCanchas() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await canchasApi.listarPublicas()
    canchas.value = Array.isArray(data) ? data : []
    canchaId.value = String(canchas.value[0]?.id || '')
  } catch {
    error.value = 'No se pudieron cargar las canchas publicadas. Inténtalo de nuevo más tarde.'
  } finally { cargando.value = false }
}
</script>

<template>
  <div class="min-h-screen bg-app-bg text-app-text">
    <header class="sticky top-0 z-20 border-b border-app-border bg-[var(--nav-bg)]">
      <div class="mx-auto flex min-h-16 max-w-7xl items-center justify-between gap-3 px-4 sm:px-8">
        <RouterLink to="/" class="flex min-w-0 items-center gap-3" aria-label="AlToque Pichanga, inicio">
          <img :src="'/logos/logo.png'" alt="" class="size-10 shrink-0 rounded-xl object-contain">
          <span class="min-w-0"><span class="block font-display text-lg leading-tight">ALTOQUE</span><span class="block text-[10px] font-bold uppercase tracking-[0.18em] text-app-text-muted">Pichanga</span></span>
        </RouterLink>
        <div class="flex items-center gap-2 sm:gap-4">
          <RouterLink v-if="auth.usuario" to="/mis-reservas" class="hidden min-h-11 items-center font-semibold text-app-link sm:inline-flex">Mis reservas</RouterLink>
          <RouterLink v-else to="/ingresar" class="hidden min-h-11 items-center font-semibold text-app-link sm:inline-flex">Mi cuenta</RouterLink>
          <ThemeSelector />
        </div>
      </div>
    </header>

    <main class="mx-auto max-w-7xl space-y-5 px-4 py-6 sm:px-8 sm:py-10">
      <RouterLink to="/" class="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-app-link"><ArrowLeft aria-hidden="true" class="size-4" />Volver al inicio</RouterLink>
      <section class="overflow-hidden rounded-3xl border border-app-border bg-[var(--hero-bg)] p-5 text-[var(--hero-text)] shadow-[var(--shadow)] sm:p-8">
        <p class="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--brand-lime)]">AlToque Pichanga · consulta pública</p>
        <h1 class="mt-3 max-w-3xl font-display text-2xl leading-tight sm:text-4xl">Horarios operativos y precios por cancha</h1>
        <p class="mt-3 max-w-3xl text-sm text-white/75 sm:text-base">Consulta las canchas que sus administradores eligieron publicar, sus intervalos y precios configurados.</p>
      </section>

      <div class="flex items-start gap-2 rounded-xl border border-[var(--status-info-text)]/30 bg-[var(--status-info-bg)] p-3 text-sm text-[var(--status-info-text)]" role="note">
        <CalendarDays aria-hidden="true" class="mt-0.5 size-4 shrink-0" />
        <p>La disponibilidad considera retenciones temporales vigentes. Selecciona bloques consecutivos para revisar el total y el adelanto mínimo del 50%; solicitar una retención no registra pagos ni confirma la reserva.</p>
      </div>

      <p v-if="error" class="rounded-xl bg-[var(--status-danger-bg)] p-4 text-sm text-[var(--status-danger-text)]" role="alert">{{ error }}</p>
      <p v-if="cargando" class="rounded-2xl border border-app-border bg-app-surface p-5 text-sm text-app-text-muted" role="status">Buscando canchas publicadas…</p>
      <section v-else-if="!canchas.length && !error" class="rounded-2xl border border-app-border bg-app-surface p-6">
        <h2 class="font-semibold">Aún no hay canchas publicadas</h2>
        <p class="mt-1 text-sm text-app-text-muted">Cuando una empresa publique sus horarios, aparecerán aquí.</p>
      </section>

      <template v-else-if="cancha">
        <section class="grid gap-4 rounded-2xl border border-app-border bg-app-surface p-4 shadow-[var(--shadow)] sm:p-5 lg:grid-cols-[minmax(0,1fr)_minmax(240px,0.8fr)] lg:items-end">
          <SelectControl id="cancha-publica" variant="public" label="Cancha publicada" :model-value="canchaId" :options="opciones" @update:model-value="canchaId = String($event)" />
          <div class="flex items-start gap-2 text-sm text-app-text-muted"><MapPin aria-hidden="true" class="mt-0.5 size-4 shrink-0" /><span>{{ ubicacion || 'Ubicación no publicada' }}</span></div>
        </section>

        <article class="grid min-w-0 gap-5 overflow-hidden rounded-2xl border border-app-border bg-app-surface shadow-[var(--shadow)] md:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div class="min-w-0">
            <img v-if="cancha.imagen_principal_url" :src="cancha.imagen_principal_url" :alt="`Cancha ${cancha.nombre}`" class="h-52 w-full object-cover sm:h-64 md:h-full md:min-h-64" loading="lazy">
            <div v-else class="grid h-52 place-items-center bg-app-surface-2 text-sm text-app-text-muted sm:h-64 md:h-full md:min-h-64">Fotografía no publicada</div>
          </div>
          <div class="min-w-0 p-4 sm:p-6">
            <p class="text-xs font-semibold uppercase tracking-wide text-app-link">{{ cancha.sede.nombre }}</p>
            <h2 class="mt-2 break-words font-display text-2xl">{{ cancha.nombre }}</h2>
            <p v-if="cancha.descripcion" class="mt-2 break-words text-sm text-app-text-muted">{{ cancha.descripcion }}</p>
            <dl class="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div><dt class="text-app-text-muted">Modalidad</dt><dd class="font-semibold">Fútbol {{ cancha.modalidad }}</dd></div>
              <div><dt class="text-app-text-muted">Superficie</dt><dd class="font-semibold">{{ cancha.tipo_superficie }}</dd></div>
              <div><dt class="text-app-text-muted">Instalaciones</dt><dd class="font-semibold">{{ cancha.techada ? 'Techada' : 'Al aire libre' }} · {{ cancha.iluminacion ? 'Iluminación' : 'Sin iluminación' }}</dd></div>
              <div v-if="cancha.capacidad_jugadores"><dt class="text-app-text-muted">Capacidad</dt><dd class="flex items-center gap-1 font-semibold"><Users aria-hidden="true" class="size-4" />{{ cancha.capacidad_jugadores }} jugadores</dd></div>
            </dl>
            <ul v-if="cancha.caracteristicas?.length" class="mt-4 flex flex-wrap gap-2" aria-label="Características">
              <li v-for="(item, indice) in cancha.caracteristicas" :key="`${cancha.id}-${indice}`" class="rounded-lg border border-app-border bg-app-surface-2 px-2.5 py-1.5 text-xs">{{ item }}</li>
            </ul>
            <p v-if="cancha.estado === 'mantenimiento'" class="mt-4 rounded-lg bg-[var(--status-warning-bg)] p-3 text-sm font-medium text-[var(--status-warning-text)]">Esta cancha está en mantenimiento. Los bloques aparecerán como cerrados.</p>
          </div>
        </article>

        <CalendarioOperativo :key="`calendario-publico-${cancha.id}`" :cancha="cancha" :publico="true" />
      </template>
    </main>
  </div>
</template>
