<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { CalendarClock, Clock3, Filter, RefreshCw, Search } from 'lucide-vue-next'
import BotonBase from '@/shared/components/BotonBase.vue'
import TablaBase from '@/shared/components/TablaBase.vue'
import DetalleReservaModal from './DetalleReservaModal.vue'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import { fechaEtiqueta, horaEtiqueta } from '@/modules/calendario/utils/fechas'
import { reservasApi } from '../services/reservas'
import { etiquetaEstadoReserva } from '../utils/reservas'

const columnas = [
  { key: 'codigo', label: 'Solicitud' },
  { key: 'jugador', label: 'Jugador' },
  { key: 'cancha', label: 'Cancha / sede' },
  { key: 'horario', label: 'Fecha y horario' },
  { key: 'duracion', label: 'Duración' },
  { key: 'importe', label: 'Total' },
  { key: 'estado', label: 'Estado' },
  { key: 'vence', label: 'Vence' },
  { key: 'acciones', label: 'Detalle' },
]
const props = defineProps({
  sedeId: { type: [Number, String], default: '' },
  empresaId: { type: [Number, String], default: '' },
})
const filtros = reactive({ q: '', estado: '', desde: '', hasta: '' })
const reservas = ref([])
const total = ref(0)
const pagina = ref(1)
const paginas = ref(1)
const cargando = ref(false)
const error = ref('')
const modalAbierto = ref(false)
const detalle = ref(null)
const cargandoDetalle = ref(false)
const vigentesPagina = computed(() => reservas.value.filter((reserva) => reserva.estado === 'retenida').length)
const siguienteVencimiento = computed(() => reservas.value
  .filter((reserva) => reserva.estado === 'retenida')
  .map((reserva) => reserva.retencion_vence_en).sort()[0] || '')

onMounted(() => cargar())

async function cargar(nuevaPagina = pagina.value) {
  cargando.value = true
  error.value = ''
  pagina.value = nuevaPagina
  try {
    const params = { page: pagina.value, page_size: 25 }
    if (props.sedeId) params.sede = props.sedeId
    if (props.empresaId) params.empresa = props.empresaId
    for (const clave of ['q', 'estado', 'desde', 'hasta']) {
      if (filtros[clave]) params[clave] = filtros[clave]
    }
    const { data } = await reservasApi.listarAdministracion(params)
    reservas.value = Array.isArray(data.results) ? data.results : []
    total.value = data.count || 0
    paginas.value = Math.max(1, Math.ceil(total.value / 25))
  } catch (fallo) {
    error.value = fallo.response?.status === 403
      ? 'Tu cuenta no tiene acceso a reservas de estas sedes.'
      : 'No se pudieron cargar las reservas. Inténtalo de nuevo.'
    reservas.value = []
  } finally { cargando.value = false }
}

async function verDetalle(reserva) {
  modalAbierto.value = true
  cargandoDetalle.value = true
  detalle.value = null
  try { detalle.value = (await reservasApi.obtenerAdministracion(reserva.codigo)).data }
  catch { modalAbierto.value = false; error.value = 'No se pudo abrir el detalle de la reserva.' }
  finally { cargandoDetalle.value = false }
}

function mostrarHorario(reserva) {
  return `${fechaEtiqueta(reserva.inicio.slice(0, 10))} · ${horaEtiqueta(reserva.inicio)}–${horaEtiqueta(reserva.fin)}`
}

function fechaVencimiento(reserva) {
  if (reserva.estado !== 'retenida') return '—'
  return new Date(reserva.retencion_vence_en).toLocaleString('es-PE', {
    timeZone: 'America/Lima', hourCycle: 'h23', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <section class="reservas-admin" aria-labelledby="reservas-admin-titulo">
    <header class="reservas-admin-heading">
      <div>
        <p class="reservas-eyebrow">Turnos de tus sedes autorizadas</p>
        <h2 id="reservas-admin-titulo">Solicitudes de reserva</h2>
        <p>Consulta retenciones y cotizaciones guardadas. La validación de pago llegará en otra fase.</p>
      </div>
      <BotonBase @click="cargar(1)"><template #icono-inicio><RefreshCw aria-hidden="true" /></template>Actualizar</BotonBase>
    </header>

    <form class="reservas-filtros" @submit.prevent="cargar(1)">
      <label class="reservas-busqueda">
        <span class="sr-only">Buscar solicitud, jugador o cancha</span>
        <Search aria-hidden="true" />
        <input v-model.trim="filtros.q" type="search" maxlength="80" placeholder="Buscar código, jugador o cancha…">
      </label>
      <label><span>Estado</span><select v-model="filtros.estado"><option value="">Todos</option><option value="retenida">Retenida</option><option value="vencida">Vencida</option><option value="cancelada">Cancelada</option></select></label>
      <label><span>Desde</span><input v-model="filtros.desde" type="date"></label>
      <label><span>Hasta</span><input v-model="filtros.hasta" type="date"></label>
      <BotonBase variante="primario" tipo="submit"><template #icono-inicio><Filter aria-hidden="true" /></template>Filtrar</BotonBase>
    </form>

    <div class="reservas-kpis" aria-label="Resumen de la consulta">
      <article><span>Solicitudes encontradas</span><strong>{{ total }}</strong><small>según los filtros actuales</small></article>
      <article><span>Retenidas en esta página</span><strong>{{ vigentesPagina }}</strong><small>de hasta 25 resultados</small></article>
      <article><span>Página</span><strong>{{ pagina }} / {{ paginas }}</strong><small>resultados paginados</small></article>
      <article><span>Próximo vencimiento en página</span><strong class="reservas-kpi-date"><CalendarClock aria-hidden="true" />{{ siguienteVencimiento ? new Date(siguienteVencimiento).toLocaleString('es-PE', { timeZone: 'America/Lima', hourCycle: 'h23', hour: '2-digit', minute: '2-digit' }) : '—' }}</strong><small>America/Lima</small></article>
    </div>

    <p v-if="error" class="reservas-error" role="alert">{{ error }}</p>
    <section class="reservas-tabla-card" aria-label="Listado de solicitudes">
      <div class="reservas-tabla-title"><div><h3>Matriz de solicitudes</h3><p>El estado aparece con etiqueta además de color.</p></div><span><Clock3 aria-hidden="true" />{{ total }} en total</span></div>
      <TablaBase :columnas="columnas" :filas="reservas" clave="codigo" :cargando="cargando" vacio="No hay solicitudes para esos filtros." etiqueta="Solicitudes de reserva">
        <template #celda-codigo="{ fila }"><strong class="reservas-codigo">{{ fila.codigo }}</strong></template>
        <template #celda-jugador="{ fila }"><span>{{ fila.jugador?.nombre || 'Jugador' }}</span><small class="reservas-secondary">{{ fila.jugador?.correo }}</small></template>
        <template #celda-cancha="{ fila }"><span>{{ fila.cancha_nombre }}</span><small class="reservas-secondary">{{ fila.sede_nombre }}</small></template>
        <template #celda-horario="{ fila }"><span class="reservas-horario">{{ mostrarHorario(fila) }}</span></template>
        <template #celda-duracion="{ fila }">{{ fila.duracion_horas }} h</template>
        <template #celda-importe="{ fila }">{{ formatearPEN(fila.importe_total, fila.moneda) }}</template>
        <template #celda-estado="{ fila }"><span class="reservas-estado" :class="`reservas-estado-${fila.estado}`">{{ etiquetaEstadoReserva(fila.estado) }}</span></template>
        <template #celda-vence="{ fila }"><span class="reservas-horario">{{ fechaVencimiento(fila) }}</span></template>
        <template #celda-acciones="{ fila }"><BotonBase tamano="pequeno" @click="verDetalle(fila)">Ver detalle</BotonBase></template>
      </TablaBase>
      <nav class="reservas-paginacion" aria-label="Páginas de solicitudes">
        <BotonBase :deshabilitado="pagina <= 1 || cargando" @click="cargar(pagina - 1)">Anterior</BotonBase>
        <span>Página {{ pagina }} de {{ paginas }}</span>
        <BotonBase :deshabilitado="pagina >= paginas || cargando" @click="cargar(pagina + 1)">Siguiente</BotonBase>
      </nav>
    </section>
    <DetalleReservaModal v-model="modalAbierto" :reserva="detalle" :cargando="cargandoDetalle" administrativa />
  </section>
</template>

<style scoped>
.reservas-admin { display: grid; min-width: 0; gap: 16px; }
.reservas-admin-heading, .reservas-tabla-title { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 12px; }
.reservas-eyebrow { margin: 0 0 4px; color: var(--link); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.reservas-admin-heading h2 { margin: 0; color: var(--text); font: 700 22px/1.25 var(--font-body); }
.reservas-admin-heading p:last-child, .reservas-tabla-title p { margin: 5px 0 0; color: var(--text-muted); font-size: 13px; }
.reservas-filtros { display: grid; grid-template-columns: minmax(220px,1.5fr) repeat(3,minmax(130px,.65fr)) auto; align-items: end; gap: 9px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 14px; }
.reservas-filtros label { display: grid; gap: 5px; color: var(--text-muted); font-size: 12px; font-weight: 600; }
.reservas-filtros input, .reservas-filtros select { width: 100%; min-height: 44px; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); padding: 8px 10px; color: var(--text); font: 500 13px var(--font-body); }
.reservas-busqueda { position: relative; display: block !important; }
.reservas-busqueda svg { position: absolute; top: 13px; left: 12px; width: 17px; height: 17px; color: var(--text-muted); }
.reservas-busqueda input { padding-left: 38px; }
.reservas-filtros :focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.reservas-kpis { display: grid; grid-template-columns: repeat(4,minmax(0,1fr)); gap: 10px; }
.reservas-kpis article { display: grid; min-width: 0; gap: 5px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 15px; }
.reservas-kpis article > span { color: var(--text-muted); font-size: 12px; font-weight: 700; }
.reservas-kpis strong { color: var(--text); font: 700 25px/1.15 var(--font-body); font-variant-numeric: tabular-nums; }
.reservas-kpis small { color: var(--text-subtle); font-size: 11px; }
.reservas-kpis .reservas-kpi-date { display: flex; align-items: center; gap: 7px; font-size: 18px; }
.reservas-kpi-date svg { width: 17px; height: 17px; color: var(--link); }
.reservas-error { margin: 0; border-radius: var(--radius-md); background: var(--danger-bg); padding: 12px; color: var(--danger); font-size: 13px; }
.reservas-tabla-card { display: grid; min-width: 0; gap: 12px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 16px; box-shadow: var(--shadow); }
.reservas-tabla-title h3 { margin: 0; color: var(--text); font: 700 17px/1.3 var(--font-body); }
.reservas-tabla-title > span { display: inline-flex; align-items: center; gap: 7px; border-radius: 999px; background: var(--surface-2); padding: 7px 10px; color: var(--text-muted); font-size: 12px; font-weight: 700; }
.reservas-tabla-title svg { width: 15px; height: 15px; color: var(--link); }
.reservas-codigo { color: var(--link); font: 700 12px/1.4 ui-monospace,monospace; white-space: nowrap; }
.reservas-secondary { display: block; margin-top: 3px; color: var(--text-muted); font-size: 11px; }
.reservas-horario { white-space: nowrap; font-variant-numeric: tabular-nums; }
.reservas-estado { display: inline-flex; max-width: 180px; border-radius: 999px; background: var(--surface-2); padding: 6px 9px; color: var(--text-muted); font-size: 11px; font-weight: 700; white-space: nowrap; }
.reservas-estado-retenida { background: var(--warning-bg); color: var(--warning); }
.reservas-estado-confirmada { background: var(--success-bg); color: var(--success); }
.reservas-paginacion { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 10px; color: var(--text-muted); font-size: 12px; }
@media (max-width: 1023px) { .reservas-filtros { grid-template-columns: repeat(2,minmax(0,1fr)); } .reservas-busqueda { grid-column: 1 / -1; } .reservas-kpis { grid-template-columns: repeat(2,minmax(0,1fr)); } }
@media (max-width: 479px) { .reservas-kpis { grid-template-columns: minmax(0,1fr); } .reservas-filtros { grid-template-columns: minmax(0,1fr); } }
</style>
