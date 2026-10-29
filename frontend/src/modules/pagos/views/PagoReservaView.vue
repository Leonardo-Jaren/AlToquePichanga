<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, RouterLink } from 'vue-router'
import { ArrowLeft, ArrowUpRight, BadgeCheck, CircleAlert, Clock3, CopyCheck, Landmark, Smartphone } from 'lucide-vue-next'
import ThemeSelector from '@/shared/components/ThemeSelector.vue'
import BotonBase from '@/shared/components/BotonBase.vue'
import { pagosApi, generarClavePago } from '../services/pagos'
import { fechaPago, soles, etiquetaEstadoPago } from '../utils/pagos'

const route = useRoute()
const reserva = ref(null)
const carga = ref(false)
const enviando = ref(false)
const error = ref('')
const aviso = ref('')
const metodoId = ref('')
const tipoPago = ref('adelanto')
const referencia = ref('')
const observacion = ref('')
const pagoActivo = computed(() => reserva.value?.pagos?.find((pago) => ['pendiente_pago', 'pendiente_revision'].includes(pago.estado)) || null)
const pagoReciente = computed(() => reserva.value?.pagos?.[0] || null)
const pagable = computed(() => reserva.value && ['retenida', 'pendiente_pago', 'pendiente_confirmacion'].includes(reserva.value.estado_reserva))
const metodoActivo = computed(() => reserva.value?.metodos?.find((metodo) => String(metodo.id) === String(metodoId.value)) || pagoActivo.value?.metodo)
const saldoVisible = computed(() => Number(reserva.value?.saldo_pendiente || 0))
const esPagoRestante = computed(() => Number(reserva.value?.importe_pagado || 0) > 0)
const montoSeleccionado = computed(() => {
  if (!reserva.value) return 0
  if (tipoPago.value === 'total') return Number(reserva.value.importe_total)
  if (tipoPago.value === 'saldo') return saldoVisible.value
  return Number(reserva.value.adelanto_minimo)
})

onMounted(cargar)

async function cargar() {
  carga.value = true
  error.value = ''
  try {
    reserva.value = (await pagosApi.obtenerReserva(route.params.codigo)).data
    const pendiente = reserva.value.pagos.find((pago) => ['pendiente_pago', 'pendiente_revision'].includes(pago.estado))
    metodoId.value = String(pendiente?.metodo.id || reserva.value.metodos[0]?.id || '')
    tipoPago.value = esPagoRestante.value ? 'saldo' : 'adelanto'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cargar el detalle del pago.'
  } finally { carga.value = false }
}

async function solicitarPago() {
  if (enviando.value || !metodoId.value || pagoActivo.value) return
  enviando.value = true
  error.value = ''
  aviso.value = ''
  try {
    await pagosApi.solicitar(route.params.codigo, {
      tipo: tipoPago.value, metodo_id: Number(metodoId.value), clave_idempotencia: generarClavePago(),
    })
    await cargar()
    aviso.value = 'Solicitud de pago creada. Revisa las instrucciones y envía tu captura por WhatsApp.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo iniciar el pago. Actualiza la página e inténtalo de nuevo.'
  } finally { enviando.value = false }
}

async function declararComprobante() {
  if (!pagoActivo.value || pagoActivo.value.estado !== 'pendiente_pago' || enviando.value) return
  enviando.value = true
  error.value = ''
  aviso.value = ''
  try {
    const { data } = await pagosApi.declarar(route.params.codigo, pagoActivo.value.id, {
      referencia: referencia.value.trim(), observacion: observacion.value.trim(),
    })
    await cargar()
    aviso.value = data.estado === 'pago_tardio'
      ? 'El horario venció. El aviso quedó registrado para conciliación manual y no confirma la reserva.'
      : 'Aviso recibido. El equipo de la sede todavía debe verificar el pago.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo registrar el aviso del comprobante.'
    await cargar()
  } finally { enviando.value = false }
}

function iconoMetodo(tipo) { return tipo === 'transferencia' ? Landmark : Smartphone }
function mostrarHorario() {
  if (!reserva.value) return ''
  const fecha = new Intl.DateTimeFormat('es-PE', { dateStyle: 'full', timeZone: 'America/Lima' }).format(new Date(reserva.value.inicio))
  const hora = (valor) => new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', hourCycle: 'h23', timeZone: 'America/Lima' }).format(new Date(valor))
  return `${fecha} · ${hora(reserva.value.inicio)}–${hora(reserva.value.fin)}`
}
</script>

<template>
  <div class="pago-view min-h-screen bg-app-bg text-app-text">
    <header class="pago-nav">
      <div class="pago-nav-inner">
        <RouterLink to="/mis-reservas" class="pago-brand" aria-label="Volver a mis reservas">
          <img :src="'/logos/logo.png'" alt="" class="size-10 rounded-xl object-contain">
          <span><strong>ALTOQUE</strong><small>Pichanga</small></span>
        </RouterLink>
        <div class="pago-nav-acciones"><RouterLink to="/mis-reservas" class="pago-back" aria-label="Volver a mis reservas"><ArrowLeft aria-hidden="true" class="size-4" /><span class="pago-back-text">Mis reservas</span></RouterLink><ThemeSelector /></div>
      </div>
    </header>

    <main class="pago-main">
      <header class="pago-heading">
        <p class="pago-eyebrow">Reserva {{ route.params.codigo }}</p>
        <h1>Pago de reserva</h1>
        <p>Elige cuánto pagar, revisa los datos de la sede y declara el comprobante cuando lo envíes.</p>
      </header>
      <ol class="pago-pasos" aria-label="Pasos para enviar el comprobante">
        <li class="pago-paso activo"><span>1</span><div><strong>Elige el monto</strong><small>Adelanto o total</small></div></li>
        <li :class="['pago-paso', pagoActivo ? 'activo' : '']"><span>2</span><div><strong>Envía por WhatsApp</strong><small>Adjunta la captura</small></div></li>
        <li :class="['pago-paso', ['pendiente_revision', 'aprobado'].includes(pagoReciente?.estado) ? 'activo' : '']"><span>3</span><div><strong>Revisión manual</strong><small>La sede confirma</small></div></li>
      </ol>

      <p v-if="error" class="pago-alerta" role="alert"><CircleAlert aria-hidden="true" />{{ error }}</p>
      <p v-if="aviso" class="pago-aviso" role="status"><BadgeCheck aria-hidden="true" />{{ aviso }}</p>
      <p v-if="carga" class="pago-card" role="status">Cargando los datos de tu reserva…</p>

      <div v-else-if="reserva" class="pago-layout">
        <section class="pago-columna">
          <article class="pago-card resumen-reserva">
            <div class="resumen-titulo"><div><p>Tu horario</p><h2>{{ reserva.cancha }}</h2><span>{{ reserva.sede }}</span></div><span class="codigo-reserva">{{ reserva.codigo }}</span></div>
            <p class="resumen-horario"><Clock3 aria-hidden="true" />{{ mostrarHorario() }}</p>
            <dl class="resumen-importes">
              <div><dt>Total de la reserva</dt><dd>{{ soles(reserva.importe_total) }}</dd></div>
              <div><dt>Adelanto mínimo · 50%</dt><dd>{{ soles(reserva.adelanto_minimo) }}</dd></div>
              <div v-if="Number(reserva.importe_pagado) > 0"><dt>Pago aprobado</dt><dd>{{ soles(reserva.importe_pagado) }}</dd></div>
              <div class="saldo"><dt>Saldo pendiente</dt><dd>{{ soles(reserva.saldo_pendiente) }}</dd></div>
            </dl>
            <p v-if="reserva.vence_en && pagable" class="vencimiento">Plazo de retención: {{ fechaPago(reserva.vence_en) }}</p>
          </article>

          <article class="pago-card estado-manual">
            <div class="estado-manual-icono"><CopyCheck aria-hidden="true" /></div>
            <div><h2>El pago se verifica en la sede</h2><p>WhatsApp solo sirve para enviar la captura. Tu reserva no queda confirmada hasta que el personal revise el pago.</p></div>
          </article>

          <article v-if="pagoReciente?.requiere_conciliacion" class="pago-alerta conciliacion" role="status">
            <CircleAlert aria-hidden="true" /><span>Se registró un pago cuando la reserva ya había vencido. La sede debe revisar la conciliación manualmente.</span>
          </article>
        </section>

        <section class="pago-card flujo-pago" aria-labelledby="elige-pago">
          <template v-if="!reserva.habilitado">
            <p class="pago-eyebrow">Pagos pausados</p><h2 id="elige-pago">Estamos preparando el flujo de pago</h2>
            <p class="texto-muted">La sede conserva tus datos de reserva. Los pagos manuales se habilitarán cuando estén definidos y aprobados los plazos de revisión.</p>
          </template>
          <template v-else-if="reserva.estado_reserva === 'vencida'">
            <span v-if="pagoReciente" :class="['estado-pago', `estado-${pagoReciente.estado}`]">{{ etiquetaEstadoPago(pagoReciente.estado) }}</span>
            <p class="pago-eyebrow">Horario liberado</p><h2 id="elige-pago">La retención venció</h2>
            <p class="texto-muted">No envíes un pago como si el horario siguiera reservado. Si ya pagaste, comunícate con la sede para la conciliación.</p>
          </template>
          <template v-else-if="pagoActivo?.estado === 'pendiente_revision'">
            <span class="estado-pago estado-pendiente_revision">{{ etiquetaEstadoPago(pagoActivo.estado) }}</span>
            <h2 id="elige-pago">La sede revisará tu comprobante</h2>
            <p class="texto-muted">Tu declaración fue recibida. El WhatsApp y la captura no aprueban el pago automáticamente.</p>
            <dl class="pago-detalle"><div><dt>Monto informado</dt><dd>{{ soles(pagoActivo.importe_solicitado) }}</dd></div><div><dt>Referencia</dt><dd>{{ pagoActivo.referencia || 'No indicada' }}</dd></div></dl>
          </template>
          <template v-else-if="pagoReciente?.estado === 'aprobado' && saldoVisible === 0">
            <span class="estado-pago estado-aprobado"><BadgeCheck aria-hidden="true" />Pago revisado</span>
            <h2 id="elige-pago">Tu reserva está pendiente de confirmación</h2>
            <p class="texto-muted">La aprobación del pago quedó registrada. La confirmación final y el ticket QR corresponden al siguiente paso del sistema.</p>
          </template>
          <template v-else>
            <p v-if="pagoReciente?.estado === 'rechazado'" class="pago-alerta compacto" role="status">
              <CircleAlert aria-hidden="true" />Comprobante rechazado. {{ pagoReciente.motivo_revision || 'Revisa la referencia y los datos del pago.' }} Puedes enviar una nueva solicitud mientras siga vigente la retención.
            </p>
            <p v-else-if="pagoReciente?.estado === 'aprobado' && saldoVisible > 0" class="pago-aviso" role="status">
              <BadgeCheck aria-hidden="true" />Tu adelanto fue verificado. Puedes pagar el saldo pendiente que muestra el resumen.
            </p>
            <p class="pago-eyebrow">Paso 1 · Selecciona cuánto pagar</p>
            <h2 id="elige-pago">¿Adelanto o pago total?</h2>
            <div class="opciones-monto" role="radiogroup" aria-label="Monto de pago">
              <label v-if="!esPagoRestante" :class="['opcion-monto', tipoPago === 'adelanto' ? 'seleccionada' : '']">
                <input v-model="tipoPago" type="radio" value="adelanto"><span><strong>Adelanto mínimo</strong><small>50% de la reserva</small></span><b>{{ soles(reserva.adelanto_minimo) }}</b>
              </label>
              <label v-if="!esPagoRestante" :class="['opcion-monto', tipoPago === 'total' ? 'seleccionada' : '']">
                <input v-model="tipoPago" type="radio" value="total"><span><strong>Pago total</strong><small>Sin saldo pendiente</small></span><b>{{ soles(reserva.importe_total) }}</b>
              </label>
              <label v-if="esPagoRestante" class="opcion-monto seleccionada">
                <input v-model="tipoPago" type="radio" value="saldo"><span><strong>Saldo pendiente</strong><small>Importe calculado por el sistema</small></span><b>{{ soles(reserva.saldo_pendiente) }}</b>
              </label>
            </div>

            <p class="pago-eyebrow metodo-eyebrow">Paso 2 · Medio de pago de la sede</p>
            <fieldset v-if="reserva.metodos.length" class="metodos-lista">
              <legend class="sr-only">Selecciona Yape, Plin o transferencia</legend>
              <label v-for="metodo in reserva.metodos" :key="metodo.id" :class="['metodo-opcion', String(metodo.id) === String(metodoId) ? 'seleccionado' : '']">
                <input v-model="metodoId" type="radio" :value="String(metodo.id)">
                <component :is="iconoMetodo(metodo.tipo)" aria-hidden="true" class="size-5" />
                <span><strong>{{ metodo.etiqueta }}</strong><small>{{ metodo.titular }}</small></span>
                <ArrowUpRight aria-hidden="true" class="size-4 flecha-metodo" />
              </label>
            </fieldset>
            <div v-else class="sin-metodos"><CircleAlert aria-hidden="true" /><span>La sede aún no configuró un medio de pago. Contacta a {{ reserva.sede }} antes de pagar.</span></div>

            <div v-if="metodoActivo" class="instrucciones-metodo" aria-live="polite">
              <div v-if="metodoActivo.imagen_qr_url" class="qr-metodo"><img :src="metodoActivo.imagen_qr_url" :alt="`QR de ${metodoActivo.etiqueta} para ${metodoActivo.titular}`"></div>
              <div class="datos-metodo"><strong>{{ metodoActivo.titular }}</strong>
                <span v-if="metodoActivo.banco">{{ metodoActivo.banco }}</span>
                <span v-if="metodoActivo.numero_cuenta">Número / cuenta: <b>{{ metodoActivo.numero_cuenta }}</b></span>
                <span v-if="metodoActivo.cci">CCI: <b>{{ metodoActivo.cci }}</b></span>
                <p v-if="metodoActivo.instrucciones">{{ metodoActivo.instrucciones }}</p>
              </div>
            </div>

            <BotonBase v-if="pagoActivo?.estado !== 'pendiente_pago'" variante="primario" tamano="grande" class="w-full" :deshabilitado="!reserva.metodos.length || !metodoId || enviando || !pagable" :cargando="enviando" @click="solicitarPago">
              {{ enviando ? 'Preparando…' : `Continuar · ${soles(montoSeleccionado)}` }}
            </BotonBase>
            <div v-else class="pago-pendiente-acciones">
              <a v-if="reserva.whatsapp_url" class="enlace-whatsapp" :href="reserva.whatsapp_url" target="_blank" rel="noopener noreferrer">
                Abrir WhatsApp para adjuntar captura <ArrowUpRight aria-hidden="true" class="size-4" />
              </a>
              <p v-else class="pago-alerta compacto" role="alert">La sede aún no configuró un WhatsApp válido. Contacta directamente a su personal.</p>
              <form class="declaracion-form" @submit.prevent="declararComprobante">
                <label><span>Referencia o código de operación <small>(opcional)</small></span><input v-model.trim="referencia" class="pago-input" maxlength="100" autocomplete="off"></label>
                <label><span>Nota para el personal <small>(opcional)</small></span><textarea v-model.trim="observacion" class="pago-input min-h-20" maxlength="240" rows="2" /></label>
                <BotonBase tipo="submit" variante="primario" class="w-full" :deshabilitado="enviando || !reserva.whatsapp_url" :cargando="enviando">Ya envié mi comprobante</BotonBase>
                <small>Este aviso no verifica el pago. El personal de la sede debe aprobarlo manualmente.</small>
              </form>
            </div>
          </template>
        </section>
      </div>
    </main>
  </div>
</template>

<style scoped>
.pago-nav { position: sticky; top: 0; z-index: 10; border-bottom: 1px solid var(--border); background: var(--nav-bg); }
.pago-nav-inner { display: flex; max-width: 1200px; min-height: 64px; align-items: center; justify-content: space-between; gap: 16px; margin: auto; padding: 8px 20px; }
.pago-brand { display: inline-flex; align-items: center; gap: 10px; color: var(--text); text-decoration: none; }
.pago-brand strong, .pago-brand small { display: block; }
.pago-brand strong { font: 400 16px var(--font-heading); }
.pago-brand small { color: var(--text-muted); font-size: 10px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }
.pago-back { display: inline-flex; min-height: 44px; align-items: center; gap: 7px; color: var(--link); font-size: 13px; font-weight: 700; text-decoration: none; }
.pago-nav-acciones { display: flex; min-width: 0; align-items: center; gap: 8px; }
.pago-main { display: grid; max-width: 1200px; gap: 22px; margin: auto; padding: 30px 20px 60px; }
.pago-heading { max-width: 760px; }
.pago-eyebrow { margin: 0 0 7px; color: var(--link); font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.pago-heading h1 { margin: 0; font: 400 clamp(30px,4vw,44px)/1.1 var(--font-heading); }
.pago-heading > p:last-child { margin: 9px 0 0; color: var(--text-muted); font-size: 14px; }
.pago-pasos { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; }
.pago-paso { display: flex; align-items: center; gap: 10px; border-bottom: 2px solid var(--border); padding: 0 2px 12px; color: var(--text-muted); }
.pago-paso > span { display: grid; width: 30px; height: 30px; place-items: center; flex: 0 0 auto; border: 1px solid var(--border-strong); border-radius: 50%; font-size: 12px; font-weight: 700; }
.pago-paso.activo { border-color: var(--brand-lime); color: var(--text); }
.pago-paso.activo > span { border-color: var(--brand-lime); background: var(--brand-lime); color: var(--on-brand-lime); }
.pago-paso strong,.pago-paso small { display: block; }
.pago-paso strong { font-size: 12px; }
.pago-paso small { margin-top: 2px; font-size: 11px; }
.pago-layout { display: grid; grid-template-columns: minmax(0,.88fr) minmax(420px,1.12fr); align-items: start; gap: 20px; }
.pago-columna { display: grid; gap: 14px; }
.pago-card { min-width: 0; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 20px; box-shadow: var(--shadow); }
.resumen-reserva { padding: 22px; }
.resumen-titulo { display: flex; flex-wrap: wrap; align-items: flex-start; justify-content: space-between; gap: 14px; }
.resumen-titulo p { margin: 0 0 4px; color: var(--text-muted); font-size: 12px; }
.resumen-titulo h2 { margin: 0; font: 700 20px/1.3 var(--font-body); }
.resumen-titulo span { display: block; margin-top: 4px; color: var(--text-muted); font-size: 13px; }
.codigo-reserva { border: 1px solid var(--border); border-radius: 8px; padding: 6px 8px; color: var(--link); font: 700 11px ui-monospace,monospace; }
.resumen-horario { display: flex; align-items: flex-start; gap: 8px; margin: 18px 0; color: var(--text-muted); font-size: 13px; line-height: 1.4; }
.resumen-horario svg { width: 17px; height: 17px; flex: 0 0 auto; color: var(--link); }
.resumen-importes { margin: 0; border-top: 1px solid var(--border); padding-top: 13px; }
.resumen-importes > div,.pago-detalle > div { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; font-size: 13px; }
.resumen-importes dt,.pago-detalle dt { color: var(--text-muted); }
.resumen-importes dd,.pago-detalle dd { margin: 0; font-weight: 700; font-variant-numeric: tabular-nums; }
.resumen-importes .saldo { margin-top: 5px; border-top: 1px solid var(--border); padding-top: 11px; font-weight: 700; }
.resumen-importes .saldo dd { color: var(--link); font-size: 16px; }
.vencimiento { margin: 12px 0 0; border-radius: 8px; background: var(--warning-bg); padding: 9px 11px; color: var(--warning); font-size: 12px; }
.estado-manual { display: flex; align-items: flex-start; gap: 12px; background: var(--surface-2); box-shadow: none; }
.estado-manual-icono { display: grid; width: 36px; height: 36px; place-items: center; flex: 0 0 auto; border-radius: 10px; background: var(--selection-bg); color: var(--link); }
.estado-manual-icono svg { width: 18px; height: 18px; }
.estado-manual h2 { margin: 0; font: 700 14px/1.35 var(--font-body); }
.estado-manual p,.texto-muted { margin: 5px 0 0; color: var(--text-muted); font-size: 13px; line-height: 1.5; }
.flujo-pago { display: grid; gap: 14px; }
.flujo-pago h2 { margin: 0; font: 700 20px/1.3 var(--font-body); }
.opciones-monto,.metodos-lista { display: grid; gap: 8px; margin: 0; padding: 0; border: 0; }
.opcion-monto { display: flex; align-items: center; gap: 11px; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 12px; cursor: pointer; }
.opcion-monto.seleccionada,.metodo-opcion.seleccionado { border-color: var(--brand-lime); background: var(--selection-bg); }
.opcion-monto input,.metodo-opcion input { width: 17px; height: 17px; accent-color: var(--brand-lime-hover); }
.opcion-monto span { flex: 1; }
.opcion-monto strong,.opcion-monto small { display: block; }
.opcion-monto strong,.metodo-opcion strong { font-size: 13px; }
.opcion-monto small,.metodo-opcion small { display: block; margin-top: 2px; color: var(--text-muted); font-size: 11px; }
.opcion-monto b { font-size: 13px; font-variant-numeric: tabular-nums; }
.metodo-eyebrow { margin-top: 3px; }
.metodo-opcion { display: flex; min-height: 58px; align-items: center; gap: 11px; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 9px 12px; cursor: pointer; }
.metodo-opcion > svg { color: var(--link); }
.metodo-opcion > span { flex: 1; }
.flecha-metodo { color: var(--text-subtle) !important; }
.instrucciones-metodo { display: flex; align-items: center; gap: 15px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface-2); padding: 12px; }
.qr-metodo img { display: block; width: 96px; height: 96px; border-radius: 8px; background: white; object-fit: contain; }
.datos-metodo { display: grid; gap: 3px; min-width: 0; color: var(--text-muted); font-size: 12px; overflow-wrap: anywhere; }
.datos-metodo strong { color: var(--text); font-size: 13px; }
.datos-metodo b { color: var(--text); font-variant-numeric: tabular-nums; }
.datos-metodo p { margin: 3px 0 0; }
.enlace-whatsapp { display: flex; min-height: 46px; align-items: center; justify-content: center; gap: 8px; border-radius: var(--radius-md); background: var(--brand-lime); padding: 10px 14px; color: var(--on-brand-lime); font-size: 13px; font-weight: 700; text-align: center; text-decoration: none; }
.enlace-whatsapp:hover { background: var(--brand-lime-hover); }
.declaracion-form { display: grid; gap: 11px; margin-top: 14px; }
.declaracion-form label span { display: block; margin-bottom: 5px; font-size: 12px; font-weight: 600; }
.declaracion-form label small,.declaracion-form > small { color: var(--text-muted); font-size: 11px; font-weight: 400; }
.declaracion-form > small { text-align: center; }
.pago-input { width: 100%; min-height: 44px; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); padding: 9px 11px; color: var(--text); font: 14px var(--font-body); }
.pago-input:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.estado-pago { display: inline-flex; width: fit-content; align-items: center; gap: 6px; border-radius: 999px; padding: 6px 9px; font-size: 11px; font-weight: 700; }
.estado-pendiente_revision { background: var(--warning-bg); color: var(--warning); }
.estado-aprobado { background: var(--success-bg); color: var(--success); }
.estado-rechazado,.estado-vencido,.estado-pago_tardio { background: var(--danger-bg); color: var(--danger); }
.estado-aprobado svg { width: 16px; height: 16px; }
.pago-detalle { margin: 5px 0 0; border-top: 1px solid var(--border); padding-top: 8px; }
.pago-alerta,.pago-aviso,.sin-metodos { display: flex; align-items: flex-start; gap: 9px; border-radius: var(--radius-md); padding: 12px 14px; font-size: 13px; line-height: 1.45; }
.pago-alerta { margin: 0; background: var(--danger-bg); color: var(--danger); }
.pago-aviso { margin: 0; background: var(--success-bg); color: var(--success); }
.pago-alerta svg,.pago-aviso svg,.sin-metodos svg { width: 18px; height: 18px; flex: 0 0 auto; }
.pago-alerta.compacto { font-size: 12px; }
.conciliacion { align-items: center; }
.sin-metodos { background: var(--warning-bg); color: var(--warning); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; clip-path: inset(50%); }
@media (max-width: 820px) { .pago-layout { grid-template-columns: 1fr; } .pago-columna { grid-template-columns: repeat(2,minmax(0,1fr)); } .resumen-reserva { grid-column: 1 / -1; } }
@media (max-width: 560px) { .pago-nav-inner,.pago-main { padding-right: 14px; padding-left: 14px; } .pago-nav-inner { gap: 8px; } .pago-main { padding-top: 22px; } .pago-back-text { display: none; } .pago-pasos { gap: 6px; } .pago-paso { align-items: flex-start; gap: 6px; padding-bottom: 8px; } .pago-paso > span { width: 24px; height: 24px; font-size: 10px; } .pago-paso strong { font-size: 10px; line-height: 1.25; } .pago-paso small { font-size: 9px; } .pago-columna { grid-template-columns: 1fr; } .resumen-reserva { grid-column: auto; } .pago-card { padding: 16px; } .resumen-reserva { padding: 18px; } .codigo-reserva { font-size: 10px; } }
</style>
