<script setup>
import { computed } from 'vue'
import { CalendarClock, Info, RotateCcw, Wallet } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import { calcularAdelantoMinimo } from '@/modules/reservas/utils/reservas'
import BotonBase from '@/shared/components/BotonBase.vue'
import { fechaEtiqueta, horaEtiqueta } from '../../utils/fechas'
import DetalleBloqueHorario from './DetalleBloqueHorario.vue'

const props = defineProps({
  detalle: { type: Object, default: null },
  seleccion: { type: Array, default: () => [] },
  cotizacion: { type: Object, default: null },
  cotizando: { type: Boolean, default: false },
  error: { type: String, default: '' },
  zonaHoraria: { type: String, default: 'America/Lima' },
  publico: { type: Boolean, default: false },
  autenticada: { type: Boolean, default: false },
  reservando: { type: Boolean, default: false },
})
const emit = defineEmits(['cotizar', 'limpiar', 'reservar'])
const inicio = computed(() => props.seleccion[0] || null)
const fin = computed(() => props.seleccion[props.seleccion.length - 1] || null)
const zonaHorariaActual = computed(() => props.zonaHoraria || 'America/Lima')
const adelantoMinimo = computed(() => calcularAdelantoMinimo(props.cotizacion?.total))
</script>

<template>
  <aside class="admin-card calendar-side-panel" aria-label="Detalle y cotización preliminar">
    <header class="calendar-side-heading">
      <div>
        <p class="calendar-side-eyebrow">Selección</p>
        <h2>Detalle del horario</h2>
      </div>
      <CalendarClock aria-hidden="true" class="size-5 text-app-link" />
    </header>

    <div v-if="detalle" class="calendar-detail-wrap">
      <DetalleBloqueHorario :detalle="detalle" :zona-horaria="zonaHorariaActual" />
    </div>
    <div v-else class="calendar-detail-empty">
      <Info aria-hidden="true" class="size-5" />
      <p>Elige un bloque de la matriz para revisar su horario, estado y tarifa.</p>
    </div>

    <section class="calendar-quote-section" aria-labelledby="cotizacion-titulo">
      <div class="calendar-quote-heading">
        <div>
          <p class="calendar-side-eyebrow">{{ publico ? 'Horario disponible' : 'Simulación · sin reserva' }}</p>
          <h3 id="cotizacion-titulo">{{ publico ? 'Precio y reserva' : 'Cotización preliminar' }}</h3>
        </div>
        <Wallet aria-hidden="true" class="size-5 text-app-link" />
      </div>

      <template v-if="seleccion.length">
        <p class="calendar-quote-summary">
          {{ seleccion.length }} {{ seleccion.length === 1 ? 'bloque' : 'bloques consecutivos' }} · {{ inicio.canchaNombre }}
        </p>
        <p class="calendar-quote-time">
          {{ fechaEtiqueta(inicio.fecha_inicio.slice(0, 10), { completa: true }) }} ·
          {{ horaEtiqueta(inicio.fecha_inicio, zonaHorariaActual) }}–{{ horaEtiqueta(fin.fecha_fin, zonaHorariaActual) }}
        </p>

        <div class="calendar-quote-actions">
          <BotonBase tamano="pequeno" @click="emit('limpiar')">
            <template #icono-inicio><RotateCcw aria-hidden="true" /></template>Limpiar
          </BotonBase>
          <BotonBase variante="primario" tamano="pequeno" :cargando="cotizando" @click="emit('cotizar')">
            {{ cotizando ? 'Calculando…' : cotizacion ? 'Actualizar' : 'Cotizar' }}
          </BotonBase>
        </div>
        <p v-if="error" class="admin-error mt-3 text-sm" role="alert">{{ error }}</p>

        <div v-if="cotizacion" class="calendar-quote-result" aria-live="polite">
          <div class="calendar-quote-total">
            <span>{{ publico ? 'Total de la reserva' : 'Total estimado' }}</span>
            <strong>{{ formatearPEN(cotizacion.total, cotizacion.moneda) }}</strong>
          </div>
          <p v-if="publico" class="calendar-advance-minimum">Adelanto mínimo del 50%: <strong>{{ formatearPEN(adelantoMinimo, cotizacion.moneda) }}</strong></p>
          <ul class="calendar-quote-items">
            <li v-for="bloque in cotizacion.bloques" :key="bloque.fecha_inicio">
              <span>{{ horaEtiqueta(bloque.fecha_inicio, zonaHorariaActual) }}–{{ horaEtiqueta(bloque.fecha_fin, zonaHorariaActual) }}</span>
              <span>{{ bloque.nombre_tarifa }} · {{ formatearPEN(bloque.precio, bloque.moneda) }}</span>
            </li>
          </ul>
          <div v-if="publico" class="calendar-booking-action">
            <BotonBase v-if="autenticada" variante="primario" :cargando="reservando" @click="emit('reservar')">
              {{ reservando ? 'Apartando…' : 'Solicitar reserva temporal' }}
            </BotonBase>
            <RouterLink v-else class="calendar-login-link" to="/ingresar">Inicia sesión para reservar</RouterLink>
          </div>
        </div>
      </template>
      <p v-else class="calendar-quote-empty">Selecciona bloques contiguos de una misma cancha para calcular un precio referencial.</p>
    </section>

    <p v-if="publico" class="calendar-no-reservation"><Info aria-hidden="true" />La retención temporal no registra un pago ni confirma la reserva.</p>
    <p v-else class="calendar-no-reservation"><Info aria-hidden="true" />La cotización no crea una reserva ni bloquea el horario.</p>
  </aside>
</template>

<style scoped>
.calendar-side-panel { align-self: start; padding: 0; overflow: hidden; }
.calendar-side-heading, .calendar-quote-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.calendar-side-heading { border-bottom: 1px solid var(--border); padding: 18px 20px 16px; }
.calendar-side-eyebrow { margin: 0 0 4px; color: var(--link); font-size: 11px; font-weight: 700; letter-spacing: .09em; text-transform: uppercase; }
.calendar-side-heading h2, .calendar-quote-heading h3 { margin: 0; color: var(--text); font: 700 17px/1.35 var(--font-body); }
.calendar-detail-wrap { margin: 16px; }
.calendar-detail-empty { display: flex; align-items: flex-start; gap: 9px; margin: 16px; border: 1px dashed var(--border-strong); border-radius: var(--radius-md); padding: 14px; color: var(--text-muted); }
.calendar-detail-empty svg { flex: 0 0 auto; color: var(--link); }
.calendar-detail-empty p { margin: 0; font-size: 13px; line-height: 1.45; }
.calendar-quote-section { border-top: 1px solid var(--border); padding: 16px 20px; }
.calendar-quote-summary { margin: 14px 0 0; color: var(--text); font-size: 14px; font-weight: 700; }
.calendar-quote-time { margin: 4px 0 0; color: var(--text-muted); font-size: 12px; line-height: 1.45; text-transform: capitalize; }
.calendar-quote-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 14px; }
.calendar-quote-actions :deep(.boton-base) { flex: 1 1 auto; }
.calendar-quote-result { margin-top: 14px; border-top: 1px solid var(--border); padding-top: 12px; }
.calendar-quote-total { display: flex; align-items: baseline; justify-content: space-between; gap: 10px; color: var(--text-muted); font-size: 13px; }
.calendar-quote-total strong { color: var(--text); font-size: 22px; font-variant-numeric: tabular-nums; }
.calendar-advance-minimum { margin: 9px 0 0; color: var(--text-muted); font-size: 13px; }
.calendar-advance-minimum strong { color: var(--text); font-variant-numeric: tabular-nums; }
.calendar-quote-items { display: grid; gap: 7px; margin: 12px 0 0; padding: 0; list-style: none; }
.calendar-quote-items li { display: grid; gap: 3px; border-radius: var(--radius-sm); background: var(--surface-2); padding: 9px 10px; color: var(--text-muted); font-size: 12px; }
.calendar-quote-items li span:first-child { color: var(--text); font-weight: 700; font-variant-numeric: tabular-nums; }
.calendar-quote-empty { margin: 14px 0 0; color: var(--text-muted); font-size: 13px; line-height: 1.5; }
.calendar-booking-action { margin-top: 14px; }
.calendar-booking-action :deep(.boton-base) { width: 100%; min-height: 48px; }
.calendar-login-link { display: grid; min-height: 44px; place-items: center; border-radius: var(--radius-md); background: var(--brand-lime); color: var(--on-brand-lime); font-size: 14px; font-weight: 700; text-decoration: none; }
.calendar-login-link:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 3px; }
.calendar-no-reservation { display: flex; align-items: flex-start; gap: 8px; border-top: 1px solid var(--border); margin: 0; padding: 14px 20px 16px; color: var(--text-muted); font-size: 12px; line-height: 1.45; }
.calendar-no-reservation svg { height: 16px; width: 16px; flex: 0 0 auto; color: var(--status-info-text); }
@media (max-width: 639px) {
  .calendar-side-heading, .calendar-quote-section, .calendar-no-reservation { padding-left: 14px; padding-right: 14px; }
}
</style>
