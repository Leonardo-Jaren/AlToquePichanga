<script setup>
import { computed, ref, watch } from 'vue'
import { BadgeCheck, CircleAlert, CircleX, Clock3, ExternalLink } from 'lucide-vue-next'
import ModalBase from '@/shared/components/ModalBase.vue'
import BotonBase from '@/shared/components/BotonBase.vue'
import { fechaPago, soles, etiquetaEstadoPago } from '../utils/pagos'

const props = defineProps({ modelValue: Boolean, pago: { type: Object, default: null }, ocupado: Boolean })
const emit = defineEmits(['update:modelValue', 'aprobar', 'rechazar'])
const importe = ref('')
const motivo = ref('')
const modoRechazo = ref(false)
const error = ref('')
const puedeRevisar = computed(() => props.pago?.estado === 'pendiente_revision' && !props.pago?.requiere_conciliacion)

watch(() => [props.modelValue, props.pago?.id], () => {
  importe.value = props.pago?.importe_solicitado || ''
  motivo.value = ''
  modoRechazo.value = false
  error.value = ''
})

function aprobar() {
  if (!Number(importe.value) || Number(importe.value) < Number(props.pago?.importe_solicitado)) {
    error.value = 'El monto verificado debe cubrir el monto solicitado.'
    return
  }
  emit('aprobar', { importe_verificado: importe.value, motivo: motivo.value.trim() })
}
function rechazar() {
  if (motivo.value.trim().length < 6) { error.value = 'Escribe un motivo claro de al menos 6 caracteres.'; return }
  emit('rechazar', { motivo: motivo.value.trim() })
}
</script>

<template>
  <ModalBase :model-value="modelValue" titulo="Revisión del pago" descripcion="Compara el comprobante recibido por WhatsApp con el importe y la reserva." ancho="grande" @update:model-value="emit('update:modelValue', $event)">
    <template v-if="pago">
      <div class="revision-grid">
        <section class="revision-resumen">
          <div class="revision-codigo"><span>Código de reserva</span><strong>{{ pago.codigo_reserva }}</strong></div>
          <span :class="['revision-estado', `estado-${pago.estado}`]">{{ etiquetaEstadoPago(pago.estado) }}</span>
          <dl class="revision-datos">
            <div><dt>Jugador</dt><dd>{{ pago.jugador?.nombre }}<small>{{ pago.jugador?.correo }}</small></dd></div>
            <div><dt>Empresa / sede</dt><dd>{{ pago.empresa }}<small>{{ pago.sede }} · {{ pago.cancha }}</small></dd></div>
            <div><dt>Medio declarado</dt><dd>{{ pago.metodo?.etiqueta }}<small>{{ pago.metodo?.titular }} · {{ pago.metodo?.numero_cuenta || pago.metodo?.banco }}</small></dd></div>
            <div><dt>Importe solicitado</dt><dd>{{ soles(pago.importe_solicitado) }}</dd></div>
            <div><dt>Referencia</dt><dd>{{ pago.referencia || 'No indicada' }}</dd></div>
            <div><dt>Declarado</dt><dd>{{ fechaPago(pago.declarado_en) }}</dd></div>
          </dl>
          <p v-if="pago.observacion_jugador" class="nota-jugador">“{{ pago.observacion_jugador }}”</p>
          <a v-if="pago.metodo?.imagen_qr_url" class="link-qr" :href="pago.metodo.imagen_qr_url" target="_blank" rel="noopener noreferrer">Ver QR configurado <ExternalLink aria-hidden="true" class="size-4" /></a>
        </section>

        <section class="revision-decision">
          <div class="aviso-manual"><CircleAlert aria-hidden="true" /><p>El personal debe comprobar el movimiento en su cuenta. La captura y la referencia no son prueba automática de pago.</p></div>
          <div v-if="pago.requiere_conciliacion" class="aviso-manual vencido"><CircleAlert aria-hidden="true" /><p>La retención venció después de recibir un pago. No apruebes para reservar este horario; requiere conciliación manual.</p></div>
          <label v-if="puedeRevisar && !modoRechazo"><span>Importe verificado</span><input v-model="importe" class="revision-input" type="number" inputmode="decimal" min="0.01" step="0.01"></label>
          <label v-if="puedeRevisar"><span>{{ modoRechazo ? 'Motivo de rechazo *' : 'Nota de revisión (opcional)' }}</span><textarea v-model.trim="motivo" class="revision-input min-h-20" rows="3" :maxlength="240" :placeholder="modoRechazo ? 'Ej.: el abono no aparece en la cuenta de la sede.' : 'Observación breve para el historial.'" /></label>
          <p v-if="error" role="alert" class="revision-error">{{ error }}</p>
          <div v-if="pago.historial?.length" class="revision-historial">
            <h3>Historial</h3>
            <ol><li v-for="(evento, indice) in pago.historial" :key="`${evento.creado_en}-${indice}`"><span><Clock3 aria-hidden="true" />{{ fechaPago(evento.creado_en) }}</span><strong>{{ evento.actor || 'Sistema' }} · {{ etiquetaEstadoPago(evento.estado_nuevo) }}</strong><small>{{ evento.motivo }}</small></li></ol>
          </div>
        </section>
      </div>
    </template>
    <template #pie>
      <BotonBase variante="secundario" :deshabilitado="ocupado" @click="emit('update:modelValue', false)">Cerrar</BotonBase>
      <template v-if="puedeRevisar && !modoRechazo && !pago?.requiere_conciliacion">
        <BotonBase variante="secundario" :deshabilitado="ocupado" @click="modoRechazo = true"><template #icono-inicio><CircleX aria-hidden="true" /></template>Rechazar</BotonBase>
        <BotonBase variante="primario" :cargando="ocupado" @click="aprobar"><template #icono-inicio><BadgeCheck aria-hidden="true" /></template>Aprobar pago</BotonBase>
      </template>
      <template v-else-if="puedeRevisar && modoRechazo">
        <BotonBase variante="secundario" :deshabilitado="ocupado" @click="modoRechazo = false">Volver</BotonBase>
        <BotonBase variante="primario" :cargando="ocupado" @click="rechazar">Confirmar rechazo</BotonBase>
      </template>
    </template>
  </ModalBase>
</template>

<style scoped>
.revision-grid { display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1fr); gap: 18px; }
.revision-resumen,.revision-decision { display: grid; align-content: start; gap: 13px; }
.revision-codigo { display: flex; justify-content: space-between; gap: 12px; color: var(--text-muted); font-size: 11px; }
.revision-codigo strong { color: var(--link); font: 700 12px ui-monospace,monospace; }
.revision-estado { width: fit-content; border-radius: 999px; background: var(--warning-bg); padding: 6px 9px; color: var(--warning); font-size: 11px; font-weight: 700; }
.revision-datos { display: grid; gap: 0; margin: 0; border-top: 1px solid var(--border); }
.revision-datos > div { display: grid; grid-template-columns: minmax(90px,.8fr) minmax(0,1.2fr); gap: 8px; border-bottom: 1px solid var(--border); padding: 9px 0; font-size: 12px; }
.revision-datos dt { color: var(--text-muted); }
.revision-datos dd { margin: 0; font-weight: 600; overflow-wrap: anywhere; }
.revision-datos dd small { display: block; margin-top: 3px; color: var(--text-muted); font-size: 11px; font-weight: 400; }
.nota-jugador { margin: 0; border-left: 3px solid var(--border-strong); padding: 8px 10px; color: var(--text-muted); font-size: 12px; }
.link-qr { display: inline-flex; align-items: center; gap: 6px; color: var(--link); font-size: 12px; font-weight: 600; }
.aviso-manual { display: flex; align-items: flex-start; gap: 8px; border-radius: var(--radius-md); background: var(--info-bg); padding: 11px; color: var(--info); }
.aviso-manual svg { width: 17px; height: 17px; flex: 0 0 auto; }
.aviso-manual p { margin: 0; font-size: 12px; line-height: 1.4; }
.aviso-manual.vencido { background: var(--danger-bg); color: var(--danger); }
.revision-decision label span { display: block; margin-bottom: 5px; font-size: 12px; font-weight: 600; }
.revision-input { width: 100%; min-height: 44px; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); padding: 9px 11px; color: var(--text); font: 13px var(--font-body); }
.revision-input:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.revision-error { margin: 0; border-radius: 8px; background: var(--danger-bg); padding: 8px; color: var(--danger); font-size: 12px; }
.revision-historial { border-top: 1px solid var(--border); padding-top: 12px; }
.revision-historial h3 { margin: 0 0 8px; font-size: 13px; }
.revision-historial ol { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; }
.revision-historial li { display: grid; gap: 3px; font-size: 11px; }
.revision-historial li > span { display: flex; align-items: center; gap: 5px; color: var(--text-muted); }
.revision-historial li svg { width: 13px; height: 13px; }
.revision-historial li small { color: var(--text-muted); line-height: 1.35; }
@media (max-width: 640px) { .revision-grid { grid-template-columns: 1fr; } }
</style>
