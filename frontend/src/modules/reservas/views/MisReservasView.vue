<script setup>
import { onMounted, ref } from 'vue'
import { ArrowLeft, CalendarClock, CircleX, RefreshCw } from 'lucide-vue-next'
import ThemeSelector from '@/shared/components/ThemeSelector.vue'
import BotonBase from '@/shared/components/BotonBase.vue'
import TablaBase from '@/shared/components/TablaBase.vue'
import { formatearPEN, mensajeErrorApi } from '@/modules/tarifas/utils/tarifas'
import { fechaEtiqueta, horaEtiqueta } from '@/modules/calendario/utils/fechas'
import DetalleReservaModal from '../components/DetalleReservaModal.vue'
import { reservasApi } from '../services/reservas'
import { etiquetaEstadoReserva } from '../utils/reservas'

const columnas = [
  { key: 'codigo', label: 'Código' }, { key: 'cancha', label: 'Cancha / sede' },
  { key: 'horario', label: 'Fecha y horario' }, { key: 'importe', label: 'Total' },
  { key: 'estado', label: 'Estado' }, { key: 'vence', label: 'Retención hasta' },
  { key: 'acciones', label: 'Detalle y pago' },
]
const reservas = ref([])
const total = ref(0)
const pagina = ref(1)
const paginas = ref(1)
const cargando = ref(false)
const cancelando = ref(false)
const error = ref('')
const aviso = ref('')
const modalAbierto = ref(false)
const confirmandoCancelacion = ref(false)
const detalle = ref(null)
const cargandoDetalle = ref(false)

onMounted(() => cargar())

async function cargar(nuevaPagina = pagina.value) {
  cargando.value = true
  error.value = ''
  pagina.value = nuevaPagina
  try {
    const { data } = await reservasApi.listarPropias({ page: pagina.value, page_size: 20 })
    reservas.value = Array.isArray(data.results) ? data.results : []
    total.value = data.count || 0
    paginas.value = Math.max(1, Math.ceil(total.value / 20))
  } catch (fallo) {
    error.value = fallo.response?.status === 401
      ? 'Tu sesión venció. Inicia sesión otra vez para consultar tus solicitudes.'
      : 'No se pudieron cargar tus reservas. Inténtalo de nuevo.'
    reservas.value = []
  } finally { cargando.value = false }
}

async function verDetalle(reserva) {
  modalAbierto.value = true
  confirmandoCancelacion.value = false
  cargandoDetalle.value = true
  detalle.value = null
  try { detalle.value = (await reservasApi.obtenerPropia(reserva.codigo)).data }
  catch { error.value = 'No se pudo abrir el detalle de esta solicitud.'; modalAbierto.value = false }
  finally { cargandoDetalle.value = false }
}

async function confirmarCancelacion() {
  if (!detalle.value || cancelando.value) return
  cancelando.value = true
  error.value = ''
  try {
    detalle.value = (await reservasApi.cancelar(detalle.value.codigo)).data
    aviso.value = detalle.value.estado === 'cancelada'
      ? 'La retención se canceló y el horario quedó libre.'
      : 'La retención venció y el horario quedó libre.'
    confirmandoCancelacion.value = false
    await cargar(pagina.value)
  } catch (fallo) {
    error.value = fallo.response?.status === 401
      ? 'Tu sesión venció. Inicia sesión otra vez.'
      : mensajeErrorApi(fallo, 'No se pudo cancelar la retención.')
  } finally { cancelando.value = false }
}

function mostrarHorario(reserva) {
  return `${fechaEtiqueta(reserva.inicio.slice(0, 10))} · ${horaEtiqueta(reserva.inicio)}–${horaEtiqueta(reserva.fin)}`
}

function fechaVencimiento(reserva) {
  return reserva.estado === 'retenida'
    ? new Date(reserva.retencion_vence_en).toLocaleString('es-PE', { timeZone: 'America/Lima', hourCycle: 'h23' })
    : '—'
}
</script>

<template>
  <div class="mis-reservas min-h-screen bg-app-bg text-app-text">
    <header class="mis-reservas-nav">
      <div class="mis-reservas-nav-inner">
        <RouterLink to="/canchas-publicas" class="mis-reservas-brand" aria-label="Volver a canchas públicas">
          <img :src="'/logos/logo.png'" alt="" class="size-10 rounded-xl object-contain">
          <span><strong>ALTOQUE</strong><small>Pichanga</small></span>
        </RouterLink>
        <div class="flex items-center gap-2"><RouterLink to="/canchas-publicas" class="min-h-11 inline-flex items-center gap-2 text-sm font-semibold text-app-link"><ArrowLeft aria-hidden="true" class="size-4" />Canchas</RouterLink><ThemeSelector /></div>
      </div>
    </header>
    <main class="mis-reservas-main">
      <header class="mis-reservas-heading">
        <div><p>Tu actividad</p><h1>Mis reservas</h1><span>Consulta el estado y el horario de cada solicitud.</span></div>
        <BotonBase @click="cargar(1)"><template #icono-inicio><RefreshCw aria-hidden="true" /></template>Actualizar</BotonBase>
      </header>
      <div class="mis-reservas-summary"><CalendarClock aria-hidden="true" /><span>{{ total }} solicitudes en tu cuenta</span><strong>Solo tú puedes consultar esta lista.</strong></div>
      <p v-if="error" class="mis-reservas-alert" role="alert">{{ error }} <RouterLink to="/ingresar">Iniciar sesión</RouterLink></p>
      <p v-if="aviso" class="mis-reservas-success" role="status">{{ aviso }}</p>
      <section class="mis-reservas-card" aria-label="Lista de mis reservas">
        <TablaBase :columnas="columnas" :filas="reservas" clave="codigo" :cargando="cargando" vacio="Todavía no tienes solicitudes de reserva." etiqueta="Mis solicitudes de reserva">
          <template #celda-codigo="{ fila }"><strong class="reserva-codigo">{{ fila.codigo }}</strong></template>
          <template #celda-cancha="{ fila }"><span>{{ fila.cancha_nombre }}</span><small class="reserva-secundaria">{{ fila.sede_nombre }}</small></template>
          <template #celda-horario="{ fila }"><span class="reserva-horario">{{ mostrarHorario(fila) }}</span></template>
          <template #celda-importe="{ fila }">{{ formatearPEN(fila.importe_total, fila.moneda) }}</template>
          <template #celda-estado="{ fila }"><span class="reserva-estado" :class="`reserva-estado-${fila.estado}`">{{ etiquetaEstadoReserva(fila.estado) }}</span></template>
          <template #celda-vence="{ fila }"><span class="reserva-horario">{{ fechaVencimiento(fila) }}</span></template>
          <template #celda-acciones="{ fila }"><div class="flex flex-wrap gap-2"><BotonBase tamano="pequeno" @click="verDetalle(fila)">Ver detalle</BotonBase><RouterLink class="enlace-pago" :to="`/mis-reservas/${fila.codigo}/pago`">Pago</RouterLink></div></template>
        </TablaBase>
        <nav class="mis-reservas-paginacion" aria-label="Páginas de reservas">
          <BotonBase :deshabilitado="pagina <= 1 || cargando" @click="cargar(pagina - 1)">Anterior</BotonBase>
          <span>Página {{ pagina }} de {{ paginas }}</span>
          <BotonBase :deshabilitado="pagina >= paginas || cargando" @click="cargar(pagina + 1)">Siguiente</BotonBase>
        </nav>
      </section>
    </main>
    <DetalleReservaModal v-model="modalAbierto" :reserva="detalle" :cargando="cargandoDetalle">
      <template #acciones>
        <template v-if="detalle?.estado === 'retenida' && !confirmandoCancelacion">
          <BotonBase variante="secundario" :deshabilitado="cancelando" @click="confirmandoCancelacion = true"><template #icono-inicio><CircleX aria-hidden="true" /></template>Cancelar retención</BotonBase>
        </template>
        <template v-else-if="detalle?.estado === 'retenida'">
          <span class="cancelar-confirmacion">¿Liberar este horario?</span>
          <BotonBase :deshabilitado="cancelando" @click="confirmandoCancelacion = false">Volver</BotonBase>
          <BotonBase variante="primario" :cargando="cancelando" @click="confirmarCancelacion">Sí, cancelar</BotonBase>
        </template>
      </template>
    </DetalleReservaModal>
  </div>
</template>

<style scoped>
.mis-reservas-nav { position: sticky; top: 0; z-index: 10; border-bottom: 1px solid var(--border); background: var(--nav-bg); }
.mis-reservas-nav-inner { display: flex; max-width: 1280px; min-height: 64px; align-items: center; justify-content: space-between; gap: 16px; margin: auto; padding: 8px 20px; }
.mis-reservas-brand { display: inline-flex; align-items: center; gap: 10px; color: var(--text); text-decoration: none; }
.mis-reservas-brand strong, .mis-reservas-brand small { display: block; }
.mis-reservas-brand strong { font: 400 16px var(--font-heading); }
.mis-reservas-brand small { color: var(--text-muted); font-size: 10px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }
.mis-reservas-main { display: grid; max-width: 1280px; gap: 18px; margin: auto; padding: 28px 20px 52px; }
.mis-reservas-heading { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 16px; }
.mis-reservas-heading p { margin: 0 0 5px; color: var(--link); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.mis-reservas-heading h1 { margin: 0; font: 400 clamp(28px,4vw,42px)/1.1 var(--font-heading); }
.mis-reservas-heading span { display: block; margin-top: 7px; color: var(--text-muted); font-size: 14px; }
.mis-reservas-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 9px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface-2); padding: 12px 14px; color: var(--text); font-size: 13px; }
.mis-reservas-summary svg { width: 17px; height: 17px; color: var(--link); }
.mis-reservas-summary strong { margin-left: auto; color: var(--text-muted); font-weight: 500; }
.mis-reservas-alert, .mis-reservas-success { margin: 0; border-radius: var(--radius-md); padding: 12px 14px; font-size: 13px; }
.mis-reservas-alert { background: var(--danger-bg); color: var(--danger); }
.mis-reservas-success { background: var(--success-bg); color: var(--success); }
.mis-reservas-alert a { color: inherit; font-weight: 700; text-decoration: underline; }
.mis-reservas-card { display: grid; gap: 14px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 16px; box-shadow: var(--shadow); }
.mis-reservas-paginacion { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 10px; color: var(--text-muted); font-size: 12px; }
.reserva-codigo { color: var(--link); font: 700 12px/1.4 ui-monospace,monospace; white-space: nowrap; }
.reserva-secundaria { display: block; margin-top: 3px; color: var(--text-muted); font-size: 11px; }
.reserva-horario { white-space: nowrap; font-variant-numeric: tabular-nums; }
.reserva-estado { display: inline-flex; border-radius: 999px; background: var(--surface-2); padding: 6px 9px; color: var(--text-muted); font-size: 11px; font-weight: 700; white-space: nowrap; }
.reserva-estado-retenida { background: var(--warning-bg); color: var(--warning); }
.reserva-estado-confirmada { background: var(--success-bg); color: var(--success); }
.cancelar-confirmacion { align-self: center; color: var(--text-muted); font-size: 12px; }
.enlace-pago { display: inline-flex; min-height: 36px; align-items: center; justify-content: center; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--selection-bg); padding: 6px 10px; color: var(--link); font-size: 12px; font-weight: 700; text-decoration: none; }
.enlace-pago:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
@media (max-width: 639px) { .mis-reservas-summary strong { width: 100%; margin-left: 26px; } .mis-reservas-nav-inner, .mis-reservas-main { padding-right: 14px; padding-left: 14px; } }
</style>
