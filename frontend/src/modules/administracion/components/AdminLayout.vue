<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  Building2, CalendarClock, CalendarDays, CircleDollarSign, ClipboardCheck, Clock3,
  CreditCard, Grid2X2, LayoutDashboard, MapPin, Menu, Settings, ShieldCheck, WalletCards,
  Users, X,
} from 'lucide-vue-next'
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

const iconosSeccion = {
  resumen: LayoutDashboard,
  empresa: Building2,
  empresas: Building2,
  sedes: MapPin,
  canchas: Grid2X2,
  horarios: Clock3,
  tarifas: CircleDollarSign,
  calendario: CalendarDays,
  reservas: CalendarClock,
  pagos: WalletCards,
  equipo: Users,
  suscripcion: CreditCard,
  planes: CreditCard,
  solicitudes: ClipboardCheck,
  vigencia: ShieldCheck,
  caja: Settings,
}

function iconoSeccion(id) { return iconosSeccion[id] || Grid2X2 }
function cambiarSeccion(id) {
  emit('cambiar-seccion', id)
  menuMovil.value = false
}

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
  <div class="admin-app-shell min-h-screen bg-app-bg text-app-text" @keydown.esc="menuMovil = false">
    <a class="admin-skip-link" href="#admin-contenido">Saltar al contenido</a>
    <button v-if="menuMovil" class="admin-sidebar-scrim" type="button" aria-label="Cerrar menú" @click="menuMovil = false" />

    <aside id="admin-side-navigation" :class="['admin-sidebar', menuMovil ? 'admin-sidebar-open' : '']" aria-label="Navegación de administración">
      <RouterLink to="/" class="admin-brand-link" @click="menuMovil = false">
        <img class="admin-logo admin-logo-light" src="/logos/logo_completo_negro.png" alt="AlToque Pichanga">
        <img class="admin-logo admin-logo-dark" src="/logos/logo_completo.png" alt="AlToque Pichanga">
      </RouterLink>

      <div v-if="secciones.length" class="admin-sidebar-navigation">
        <p class="admin-sidebar-caption">Administración</p>
        <nav class="admin-nav" aria-label="Secciones">
          <button v-for="seccion in secciones" :key="seccion.id" type="button"
            :class="['admin-nav-link', activa === seccion.id ? 'admin-nav-link-active' : '']"
            :aria-current="activa === seccion.id ? 'page' : undefined"
            @click="cambiarSeccion(seccion.id)">
            <component :is="iconoSeccion(seccion.id)" aria-hidden="true" class="size-5 shrink-0" />
            <span class="min-w-0 flex-1 truncate">{{ seccion.nombre }}</span>
            <span v-if="activa === seccion.id" class="admin-nav-line" aria-hidden="true" />
          </button>
        </nav>
      </div>

      <div v-if="$slots.sidebar" class="admin-sidebar-extra"><slot name="sidebar" /></div>
      <footer class="admin-sidebar-footer">
        <span class="admin-sidebar-footer-mark" aria-hidden="true" />
        <span>Tu pichanga, al toque.</span>
      </footer>
    </aside>

    <div class="admin-main-shell">
      <header class="admin-topbar">
        <div class="admin-topbar-inner">
          <button class="admin-mobile-menu" type="button" :aria-expanded="menuMovil"
            aria-controls="admin-side-navigation" :aria-label="menuMovil ? 'Cerrar navegación' : 'Abrir navegación'"
            @click="menuMovil = !menuMovil">
            <X v-if="menuMovil" aria-hidden="true" class="size-5" />
            <Menu v-else aria-hidden="true" class="size-5" />
          </button>
          <div class="admin-topbar-context">
            <span class="admin-topbar-context-mark" aria-hidden="true" />
            <span>Panel de administración</span>
          </div>
          <div class="admin-topbar-actions">
            <ThemeSelector />
            <span class="admin-user-name" :title="auth.usuario?.nombre">{{ auth.usuario?.nombre }}</span>
            <button class="admin-button admin-button-quiet admin-logout" type="button" @click="salir">
              <span class="hidden sm:inline">Cerrar sesión</span><span class="sm:hidden">Salir</span>
            </button>
          </div>
        </div>
      </header>

      <main id="admin-contenido" class="admin-content" tabindex="-1">
        <section class="admin-page-heading" aria-labelledby="admin-titulo">
          <div class="admin-field-mark" aria-hidden="true" />
          <div class="min-w-0">
            <p class="admin-page-eyebrow">AlToque · Gestión</p>
            <h1 id="admin-titulo">{{ titulo }}</h1>
            <p v-if="descripcion" class="admin-page-description">{{ descripcion }}</p>
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
