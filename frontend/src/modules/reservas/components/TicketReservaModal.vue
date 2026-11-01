<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import ModalBase from '@/shared/components/ModalBase.vue'
import BotonBase from '@/shared/components/BotonBase.vue'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import { fechaEtiqueta, horaEtiqueta } from '@/modules/calendario/utils/fechas'
import { reservasApi } from '../services/reservas'

const props = defineProps({ modelValue: Boolean, codigo: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])
const ticket = ref(null)
const qr = ref('')
const cargando = ref(false)
const error = ref('')
let carga = 0

function liberarQr() {
  if (qr.value) URL.revokeObjectURL(qr.value)
  qr.value = ''
}
watch(() => [props.modelValue, props.codigo], async ([abierto, codigo]) => {
  const intento = ++carga
  liberarQr()
  ticket.value = null
  error.value = ''
  if (!abierto || !codigo) return
  cargando.value = true
  try {
    const [datos, imagen] = await Promise.all([reservasApi.ticket(codigo), reservasApi.ticketQr(codigo)])
    if (intento !== carga) return
    ticket.value = datos.data
    qr.value = URL.createObjectURL(imagen.data)
  } catch {
    if (intento === carga) error.value = 'No se pudo cargar el ticket. Actualiza e inténtalo otra vez.'
  } finally {
    if (intento === carga) cargando.value = false
  }
}, { immediate: true })
onBeforeUnmount(() => { carga++; liberarQr() })
</script>

<template>
  <ModalBase :model-value="modelValue" titulo="Tu ticket" descripcion="Preséntalo en la sede al llegar."
    @update:model-value="emit('update:modelValue', $event)">
    <p v-if="cargando" role="status">Preparando tu ticket…</p>
    <p v-else-if="error" role="alert">{{ error }}</p>
    <article v-else-if="ticket" class="ticket">
      <header class="ticket-header"><img :src="'/logos/logo.png'" alt="AlToque Pichanga"><span>Reserva confirmada</span></header>
      <div class="ticket-destino"><p>{{ ticket.sede }}</p><h3>{{ ticket.cancha }}</h3><strong>{{ ticket.codigo }}</strong></div>
      <div class="ticket-qr"><img :src="qr" alt="Código QR de la reserva confirmada"></div>
      <p class="ticket-caption">Muestra este código al personal de la sede.</p>
      <dl class="ticket-datos">
        <div><dt>Fecha y hora · Perú</dt><dd>{{ fechaEtiqueta(ticket.inicio.slice(0, 10)) }} · {{ horaEtiqueta(ticket.inicio) }}–{{ horaEtiqueta(ticket.fin) }}</dd></div>
        <div><dt>Jugador</dt><dd>{{ ticket.jugador }}</dd></div>
        <div><dt>Total</dt><dd>{{ formatearPEN(ticket.importe_total, ticket.moneda) }}</dd></div>
        <div><dt>Pagado</dt><dd>{{ formatearPEN(ticket.importe_pagado, ticket.moneda) }}</dd></div>
        <div><dt>Saldo pendiente</dt><dd>{{ formatearPEN(ticket.saldo_pendiente, ticket.moneda) }}</dd></div>
      </dl>
      <details><summary>Condiciones de cancelación</summary><p class="ticket-condiciones">{{ ticket.condiciones_cancelacion || 'No se registraron condiciones en esta solicitud; consulta a la sede.' }}</p></details>
      <a v-if="qr" class="ticket-descarga" :href="qr" :download="`qr-${ticket.codigo}.svg`">Descargar QR</a>
    </article>
    <template #pie><BotonBase @click="emit('update:modelValue', false)">Cerrar</BotonBase></template>
  </ModalBase>
</template>

<style scoped>
.ticket { display: grid; gap: 16px; }
.ticket-header { display: flex; align-items: center; justify-content: space-between; border-radius: var(--radius-md); background: var(--brand-charcoal); padding: 12px 16px; color: var(--brand-white); }
.ticket-header img { width: 74px; max-height: 48px; object-fit: contain; }
.ticket-header span { border-radius: 999px; background: var(--brand-lime); padding: 5px 10px; color: var(--on-brand-lime); font-size: 12px; font-weight: 700; }
.ticket-destino p, .ticket-destino h3 { margin: 0; }
.ticket-destino p, .ticket-caption, dt { color: var(--text-muted); font-size: 13px; }
.ticket-destino h3 { margin: 3px 0; font-size: 22px; }
.ticket-destino strong { color: var(--link); font-variant-numeric: tabular-nums; }
.ticket-qr { justify-self: center; border-radius: var(--radius-md); background: var(--brand-white); padding: 8px; }
.ticket-qr img { display: block; width: min(56vw, 230px); height: auto; }
.ticket-caption { margin: 0; text-align: center; }
.ticket-datos { display: grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: 12px; margin: 0; border-top: 1px dashed var(--border-strong); padding-top: 16px; }
.ticket-datos div:first-child { grid-column: 1 / -1; }
.ticket-datos dd { margin: 3px 0 0; font-weight: 600; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }
.ticket-condiciones { color: var(--text-muted); white-space: pre-wrap; }
.ticket-descarga { display: flex; min-height: 44px; align-items: center; justify-content: center; border-radius: var(--radius-md); background: var(--brand-lime); color: var(--on-brand-lime); font-weight: 700; text-decoration: none; }
</style>
