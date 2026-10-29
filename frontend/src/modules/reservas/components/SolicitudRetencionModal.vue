<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { CheckCircle2, Clock3, Info } from 'lucide-vue-next'
import { RouterLink } from 'vue-router'
import { useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'
import { formatearPEN, mensajeErrorApi } from '@/modules/tarifas/utils/tarifas'
import BotonBase from '@/shared/components/BotonBase.vue'
import ModalBase from '@/shared/components/ModalBase.vue'
import { fechaEtiqueta, horaEtiqueta, horaLocalISO } from '@/modules/calendario/utils/fechas'
import { generarClaveIdempotencia, reservasApi } from '../services/reservas'
import { calcularAdelantoMinimo, formatoCuentaRegresiva, segundosRestantes } from '../utils/reservas'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  cancha: { type: Object, required: true },
  seleccion: { type: Array, default: () => [] },
  cotizacion: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'reservada', 'conflicto'])
const auth = useAutenticacionStore()
const resultado = ref(null)
const cargando = ref(false)
const error = ref('')
const ahora = ref(Date.now())
let claveIntento = ''
let reloj = null

const inicio = computed(() => props.seleccion[0] || null)
const fin = computed(() => props.seleccion[props.seleccion.length - 1] || null)
const adelantoEstimado = computed(() => calcularAdelantoMinimo(props.cotizacion?.total))
const restante = computed(() => segundosRestantes(resultado.value?.retencion_vence_en, ahora.value))
const fechaReserva = computed(() => inicio.value
  ? fechaEtiqueta(inicio.value.fecha_inicio.slice(0, 10), { completa: true })
  : 'Selecciona un horario')
const horaReserva = computed(() => inicio.value
  ? `${horaEtiqueta(inicio.value.fecha_inicio)}–${horaEtiqueta(fin.value.fecha_fin)}` : '')

watch(() => props.modelValue, (abierto) => {
  if (abierto) {
    resultado.value = null
    error.value = ''
    claveIntento = ''
  }
})

onMounted(() => { reloj = window.setInterval(() => { ahora.value = Date.now() }, 1000) })
onUnmounted(() => window.clearInterval(reloj))

async function solicitar() {
  if (!auth.usuario || !inicio.value || !props.cotizacion || cargando.value) return
  cargando.value = true
  error.value = ''
  claveIntento ||= generarClaveIdempotencia()
  try {
    const { data } = await reservasApi.solicitar({
      cancha_id: props.cancha.id,
      fecha: inicio.value.fecha_inicio.slice(0, 10),
      hora_inicio: horaLocalISO(inicio.value.fecha_inicio),
      duracion_horas: props.seleccion.length,
      clave_idempotencia: claveIntento,
    })
    resultado.value = data
    emit('reservada', data)
  } catch (fallo) {
    if (fallo.response?.status === 409) {
      error.value = 'Ese horario acaba de ocuparse. Actualizamos el calendario; elige otro bloque.'
      emit('conflicto')
    } else if (fallo.response?.status === 401) {
      error.value = 'Tu sesión venció. Inicia sesión otra vez y vuelve a elegir el horario.'
    } else {
      error.value = mensajeErrorApi(fallo, 'No se pudo solicitar esta retención. Revisa el horario e inténtalo de nuevo.')
    }
  } finally { cargando.value = false }
}
</script>

<template>
  <ModalBase :model-value="modelValue" titulo="Solicitar retención temporal"
    descripcion="Revisa el horario y el importe antes de apartarlo." ancho="mediano"
    @update:model-value="emit('update:modelValue', $event)">
    <section v-if="resultado" class="solicitud-resultado" aria-live="polite">
      <p class="solicitud-confirmada"><CheckCircle2 aria-hidden="true" />Horario retenido temporalmente</p>
      <p class="solicitud-codigo">Código {{ resultado.codigo }}</p>
      <dl>
        <div><dt>Estado</dt><dd>Retenida temporalmente</dd></div>
        <div><dt>Total de la reserva</dt><dd>{{ formatearPEN(resultado.importe_total, resultado.moneda) }}</dd></div>
        <div><dt>Adelanto mínimo para continuar</dt><dd>{{ formatearPEN(resultado.adelanto_minimo, resultado.moneda) }}</dd></div>
        <div><dt>Tiempo restante</dt><dd class="tabular-nums">{{ restante ? formatoCuentaRegresiva(restante) : 'Vencida; actualiza el calendario' }}</dd></div>
      </dl>
      <p class="solicitud-nota">Esta retención no registra un pago y todavía no confirma la reserva.</p>
    </section>
    <section v-else class="solicitud-resumen">
      <dl>
        <div><dt>Cancha</dt><dd>{{ cancha.nombre }}</dd></div>
        <div><dt>Fecha</dt><dd class="capitalize">{{ fechaReserva }}</dd></div>
        <div><dt>Horario</dt><dd class="tabular-nums">{{ horaReserva }} · {{ seleccion.length }} h</dd></div>
        <div><dt>Total estimado</dt><dd>{{ formatearPEN(cotizacion?.total, cotizacion?.moneda) }}</dd></div>
        <div><dt>Adelanto mínimo (50%)</dt><dd>{{ adelantoEstimado ? formatearPEN(adelantoEstimado, cotizacion?.moneda) : '—' }}</dd></div>
      </dl>
      <p class="solicitud-nota"><Info aria-hidden="true" />La retención aparta el horario por un plazo provisional. No realiza cobros ni confirma la reserva.</p>
      <p v-if="error" class="solicitud-error" role="alert">{{ error }}</p>
      <p v-if="!auth.usuario" class="solicitud-login">Para reservar, <RouterLink to="/ingresar">inicia sesión</RouterLink> y vuelve a seleccionar el horario.</p>
    </section>
    <template #pie>
      <BotonBase variante="primario" :deshabilitado="!auth.usuario || !cotizacion || !seleccion.length"
        :cargando="cargando" @click="resultado ? emit('update:modelValue', false) : solicitar()">
        {{ resultado ? 'Listo' : cargando ? 'Apartando…' : 'Apartar horario' }}
      </BotonBase>
    </template>
  </ModalBase>
</template>

<style scoped>
.solicitud-resumen, .solicitud-resultado { display: grid; gap: 16px; }
.solicitud-resumen dl, .solicitud-resultado dl { display: grid; gap: 8px; margin: 0; }
.solicitud-resumen dl > div, .solicitud-resultado dl > div { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 8px; border-radius: var(--radius-md); background: var(--surface-2); padding: 11px 13px; }
.solicitud-resumen dt, .solicitud-resultado dt { color: var(--text-muted); font-size: 13px; }
.solicitud-resumen dd, .solicitud-resultado dd { margin: 0; color: var(--text); font-size: 14px; font-weight: 700; text-align: right; }
.solicitud-nota { display: flex; align-items: flex-start; gap: 8px; margin: 0; border-left: 3px solid var(--brand-lime); padding-left: 10px; color: var(--text-muted); font-size: 12px; line-height: 1.45; }
.solicitud-nota :deep(svg) { width: 16px; height: 16px; flex: 0 0 auto; color: var(--link); }
.solicitud-error { margin: 0; border-radius: var(--radius-md); background: var(--danger-bg); padding: 11px 13px; color: var(--danger); font-size: 13px; }
.solicitud-login { margin: 0; color: var(--text-muted); font-size: 13px; }
.solicitud-login a { color: var(--link); font-weight: 700; text-decoration: underline; text-underline-offset: 3px; }
.solicitud-confirmada { display: flex; align-items: center; gap: 9px; margin: 0; color: var(--success); font-size: 17px; font-weight: 700; }
.solicitud-confirmada :deep(svg) { width: 21px; height: 21px; flex: 0 0 auto; }
.solicitud-codigo { margin: -9px 0 0; color: var(--text-muted); font: 600 13px/1.4 ui-monospace, monospace; }
@media (prefers-reduced-motion: reduce) { .solicitud-resumen *, .solicitud-resultado * { scroll-behavior: auto; } }
</style>
