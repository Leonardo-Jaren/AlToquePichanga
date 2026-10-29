<script setup>
import { ref, onMounted } from 'vue'
import { Activity, CheckCircle2, AlertTriangle, RefreshCw, Database, Server, Sparkles } from 'lucide-vue-next'
import ThemeSelector from '@/shared/components/ThemeSelector.vue'
import api from '@/shared/services/api'

const healthData = ref(null)
const cargando = ref(false)
const errorMensaje = ref('')
const ultimaConsulta = ref(null)

async function consultarSaludBackend() {
  cargando.value = true
  errorMensaje.value = ''
  try {
    const respuesta = await api.get('/health/')
    healthData.value = respuesta.data
    ultimaConsulta.value = new Date().toLocaleTimeString('es-PE')
  } catch (err) {
    healthData.value = null
    errorMensaje.value = err.message || 'No se pudo conectar con el backend Django'
  } finally {
    cargando.value = false
  }
}

onMounted(() => {
  consultarSaludBackend()
})
</script>

<template>
  <div class="min-h-screen bg-[var(--bg)] text-[var(--text)] transition-colors duration-200">
    <!-- Barra superior / Header -->
    <header class="border-b border-[var(--border)] bg-[var(--nav-bg)] sticky top-0 z-50 transition-colors">
      <div class="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        <div class="flex items-center gap-3">
          <img
            :src="'/logos/logo.png'"
            alt="Logo AlToque Pichanga"
            class="w-10 h-10 object-contain rounded-lg shadow-sm"
          />
          <div class="flex flex-col leading-none">
            <span class="font-display text-xl tracking-tight text-[var(--text)] uppercase">
              AlToque
            </span>
            <span class="text-[10px] uppercase font-bold tracking-widest text-[var(--text-muted)]">
              Pichanga
            </span>
          </div>
        </div>

        <div class="flex items-center gap-4">
          <RouterLink to="/canchas-publicas" class="hidden text-sm font-semibold text-[var(--link)] sm:inline">Horarios y precios</RouterLink>
          <a href="/ingresar" class="text-sm font-semibold text-[var(--link)]">Mi cuenta</a>
          <span class="hidden sm:inline-block text-xs font-medium text-[var(--text-muted)] bg-[var(--surface-2)] px-2.5 py-1 rounded-full border border-[var(--border)]">
            Fase 0 — Inicialización
          </span>
          <ThemeSelector />
        </div>
      </div>
    </header>

    <!-- Contenido Principal -->
    <main class="max-w-6xl mx-auto px-4 sm:px-6 py-10 space-y-8">
      <!-- Sección Hero -->
      <section class="rounded-2xl p-8 sm:p-12 bg-[var(--hero-bg)] text-[var(--hero-text)] border border-[var(--border-strong)] relative overflow-hidden shadow-[var(--shadow)]">
        <div class="max-w-2xl relative z-10 space-y-4">
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--brand-lime-dark)] border border-[var(--brand-lime)]/30 text-[var(--brand-lime)] text-xs font-medium">
            <Sparkles class="w-3.5 h-3.5 text-[var(--brand-lime)]" />
            <span>SaaS Multiempresa para Gestión Deportiva</span>
          </div>

          <h1 class="font-display text-3xl sm:text-5xl uppercase tracking-tight text-white leading-tight">
            Tu pichanga, <span class="text-[var(--brand-lime)]">al toque.</span>
          </h1>

          <p class="text-sm sm:text-base text-gray-300 leading-relaxed font-normal">
            Plataforma para descubrir, reservar y gestionar canchas de fútbol con control de tarifas diurnas/nocturnas, validación de señas y concurrencia garantizada.
          </p>
        </div>
      </section>

      <!-- Panel de Verificación de Integración Backend / Django -->
      <section class="rounded-2xl p-6 sm:p-8 bg-[var(--surface)] border border-[var(--border)] shadow-[var(--shadow)] space-y-6">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-5">
          <div class="flex items-center gap-3">
            <div class="p-2.5 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] text-[var(--text)]">
              <Activity class="w-5 h-5 text-[var(--brand-lime)]" />
            </div>
            <div>
              <h2 class="text-lg font-bold text-[var(--text)] flex items-center gap-2">
                Estado de la Conexión Backend
              </h2>
              <p class="text-xs text-[var(--text-muted)]">
                Comprobación en tiempo real del endpoint Django REST Framework: <code class="bg-[var(--surface-2)] px-1.5 py-0.5 rounded text-[var(--text)] font-mono text-xs">/api/health/</code>
              </p>
            </div>
          </div>

          <button
            type="button"
            :disabled="cargando"
            class="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-[var(--brand-lime)] hover:bg-[var(--brand-lime-hover)] active:bg-[var(--brand-lime-pressed)] text-[var(--on-brand-lime)] font-semibold text-xs tracking-wide transition-colors cursor-pointer disabled:opacity-50 shadow-sm"
            @click="consultarSaludBackend"
          >
            <RefreshCw :class="['w-4 h-4', { 'animate-spin': cargando }]" />
            <span>{{ cargando ? 'Consultando...' : 'Reconsultar Endpoint' }}</span>
          </button>
        </div>

        <!-- Tarjetas de diagnóstico -->
        <div v-if="healthData" class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <!-- Tarjeta Servicio -->
          <div class="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-[var(--text-muted)] flex items-center gap-1.5">
                <Server class="w-3.5 h-3.5" /> API Django
              </span>
              <span class="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md text-[var(--status-success-text)] bg-[var(--status-success-bg)]">
                <CheckCircle2 class="w-3 h-3" /> {{ healthData.estado }}
              </span>
            </div>
            <p class="text-sm font-semibold text-[var(--text)]">{{ healthData.servicio }}</p>
            <p class="text-xs text-[var(--text-muted)] font-mono">v{{ healthData.version }} ({{ healthData.fase }})</p>
          </div>

          <!-- Tarjeta Base de Datos -->
          <div class="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-[var(--text-muted)] flex items-center gap-1.5">
                <Database class="w-3.5 h-3.5" /> PostgreSQL
              </span>
              <span
                :class="[
                  'inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md',
                  healthData.base_de_datos === 'conectada'
                    ? 'text-[var(--status-success-text)] bg-[var(--status-success-bg)]'
                    : 'text-[var(--status-danger-text)] bg-[var(--status-danger-bg)]',
                ]"
              >
                {{ healthData.base_de_datos }}
              </span>
            </div>
            <p class="text-sm font-semibold text-[var(--text)]">PostgreSQL 17 Nativo</p>
            <p class="text-xs text-[var(--text-muted)] font-mono">Consultas activas verificadas</p>
          </div>

          <!-- Tarjeta Timestamp -->
          <div class="p-4 rounded-xl bg-[var(--surface-2)] border border-[var(--border)] space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-xs font-medium text-[var(--text-muted)]">Última Respuesta</span>
              <span class="text-[11px] font-mono text-[var(--text-subtle)]">{{ ultimaConsulta }}</span>
            </div>
            <p class="text-xs text-[var(--text)] font-mono break-all">{{ healthData.timestamp }}</p>
            <p class="text-xs text-[var(--status-success-text)] font-medium">✓ Sincronización exitosa</p>
          </div>
        </div>

        <!-- Estado de Error -->
        <div v-else-if="errorMensaje" class="p-4 rounded-xl border border-[var(--status-danger-text)]/30 bg-[var(--status-danger-bg)] text-[var(--status-danger-text)] flex items-start gap-3">
          <AlertTriangle class="w-5 h-5 shrink-0 mt-0.5" />
          <div class="space-y-1">
            <p class="text-xs font-bold uppercase tracking-wider">Aviso de conexión</p>
            <p class="text-xs">{{ errorMensaje }}</p>
            <p class="text-[11px] opacity-80">Asegúrate de que el servidor Django esté corriendo en http://localhost:8000</p>
          </div>
        </div>
      </section>

      <!-- Panel de Tokens de Diseño y Tipografía -->
      <section class="rounded-2xl p-6 bg-[var(--surface)] border border-[var(--border)] space-y-4">
        <h3 class="text-sm font-bold uppercase tracking-wider text-[var(--text-muted)]">
          Especificación de Tokens Visuales (AGENTS.md)
        </h3>
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
          <div class="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] space-y-1">
            <div class="w-full h-6 rounded bg-[#C0FA04] border border-black/10"></div>
            <p class="font-bold text-[var(--text)]">Brand Lime</p>
            <p class="text-[var(--text-muted)] font-mono">#C0FA04</p>
          </div>
          <div class="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] space-y-1">
            <div class="w-full h-6 rounded bg-[#0B0F12] border border-white/10"></div>
            <p class="font-bold text-[var(--text)]">Brand Charcoal</p>
            <p class="text-[var(--text-muted)] font-mono">#0B0F12</p>
          </div>
          <div class="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] space-y-1">
            <div class="w-full h-6 rounded bg-[var(--surface)] border border-[var(--border)]"></div>
            <p class="font-bold text-[var(--text)]">Surface</p>
            <p class="text-[var(--text-muted)] font-mono">var(--surface)</p>
          </div>
          <div class="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] space-y-1">
            <div class="w-full h-6 rounded bg-[var(--selection-bg)] border border-[var(--border)]"></div>
            <p class="font-bold text-[var(--text)]">Selection</p>
            <p class="text-[var(--text-muted)] font-mono">var(--selection-bg)</p>
          </div>
        </div>
      </section>
    </main>
  </div>
</template>
