<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import {
  CalendarClock, CalendarDays, CircleCheck, Clock3, Grid2X2, Info, RefreshCw, Tag,
} from 'lucide-vue-next'
import { tarifasApi } from '@/modules/tarifas/services/tarifas'
import { reservasApi } from '@/modules/reservas/services/reservas'
import { formatearPEN, mensajeErrorApi } from '@/modules/tarifas/utils/tarifas'
import BotonBase from '@/shared/components/BotonBase.vue'
import { bloquePuedeCotizar } from '../../utils/bloques'
import { useDisponibilidadTiempoReal } from '../../composables/useDisponibilidadTiempoReal'
import {
  desplazarFecha, diasEntre, fechaActualLima, fechaEtiqueta,
  horaLocalISO, rangoCalendario,
} from '../../utils/fechas'
import MatrizHorarioCanchas from './MatrizHorarioCanchas.vue'
import ResumenCalendarioLateral from './ResumenCalendarioLateral.vue'
import SelectorPeriodoCalendario from './SelectorPeriodoCalendario.vue'
import TarjetaResumenCalendario from './TarjetaResumenCalendario.vue'
import DialogoDetalleHorario from './DialogoDetalleHorario.vue'
import EstadoDisponibilidadTiempoReal from './EstadoDisponibilidadTiempoReal.vue'

const props = defineProps({ canchas: { type: Array, default: () => [] } })

const vista = ref('dia')
const fecha = ref(fechaActualLima())
const fechaActiva = ref(fechaActualLima())
const bloquesPorCancha = ref({})
const zonaHoraria = ref('America/Lima')
const cargando = ref(false)
const consultado = ref(false)
const error = ref('')
const seleccion = ref([])
const detalle = ref(null)
const detalleEnDialogo = ref(false)
const vistaCompacta = ref(false)
const cotizacion = ref(null)
const cotizando = ref(false)
const errorSeleccion = ref('')
let solicitudConsulta = 0
let solicitudCotizacion = 0
let consultaPantallaCompacta = null
const rango = computed(() => rangoCalendario(vista.value, fecha.value))
const dias = computed(() => diasEntre(rango.value.desde, rango.value.hasta))
const idsCanchas = computed(() => props.canchas.map((cancha) => String(cancha.id)).join(','))
const fechaTitulo = computed(() => fechaEtiqueta(fechaActiva.value, { completa: true }))

const bloquesDelDia = computed(() => props.canchas.flatMap((cancha) => {
  const datos = bloquesPorCancha.value[String(cancha.id)]
  return (datos?.bloques || [])
    .filter((bloque) => bloque.fecha_inicio?.slice(0, 10) === fechaActiva.value)
    .map((bloque) => ({ ...bloque, canchaId: String(cancha.id), canchaNombre: cancha.nombre, zonaHoraria: datos.zonaHoraria }))
}))

const horas = computed(() => [...new Set(bloquesDelDia.value.map((bloque) => bloque.fecha_inicio))]
  .sort((a, b) => Date.parse(a) - Date.parse(b)))

const filas = computed(() => props.canchas.map((cancha) => {
  const bloques = bloquesDelDia.value.filter((bloque) => bloque.canchaId === String(cancha.id))
  return {
    id: String(cancha.id),
    nombre: cancha.nombre,
    estado: cancha.estado,
    mapaBloques: Object.fromEntries(bloques.map((bloque) => [bloque.fecha_inicio, bloque])),
  }
}))

const estadisticas = computed(() => ({
  total: bloquesDelDia.value.length,
  operativos: bloquesDelDia.value.filter(bloquePuedeCotizar).length,
  retenidos: bloquesDelDia.value.filter((bloque) => bloque.estado_reserva).length,
  excepciones: bloquesDelDia.value.filter((bloque) => bloque.origen === 'ampliacion_excepcional').length,
}))

const tarjetasEstadistica = computed(() => [
  { id: 'bloques', titulo: 'Bloques horarios', valor: estadisticas.value.total, descripcion: `en ${fechaTitulo.value}`, icono: Grid2X2, tono: 'marca' },
  { id: 'operativos', titulo: 'Libres para reservar', valor: estadisticas.value.operativos, descripcion: 'horario operativo y con tarifa', icono: CircleCheck, tono: 'exito' },
  { id: 'retenidos', titulo: 'Retenciones vigentes', valor: estadisticas.value.retenidos, descripcion: 'ocupan estos horarios', icono: Clock3, tono: 'info' },
  { id: 'excepciones', titulo: 'Bloques ampliados', valor: estadisticas.value.excepciones, descripcion: 'por excepción de horario', icono: Tag, tono: 'tarifa' },
])

const tiempoReal = useDisponibilidadTiempoReal({
  canchas: idsCanchas,
  desde: computed(() => rango.value.desde),
  hasta: computed(() => rango.value.hasta),
  alCambiar: () => { void consultar({ preservarSeleccion: true }) },
  alRecuperar: () => { void consultar({ preservarSeleccion: true }) },
})

watch([vista, fecha], () => {
  if (vista.value === 'dia') fechaActiva.value = fecha.value
  else if (!dias.value.includes(fechaActiva.value)) fechaActiva.value = rango.value.desde
}, { immediate: true })

watch([vista, () => rango.value.desde, () => rango.value.hasta, idsCanchas], consultar, { immediate: true })

onMounted(() => {
  if (typeof window.matchMedia !== 'function') return
  consultaPantallaCompacta = window.matchMedia('(max-width: 1023px)')
  vistaCompacta.value = consultaPantallaCompacta.matches
  consultaPantallaCompacta.addEventListener('change', actualizarVistaCompacta)
})

onUnmounted(() => consultaPantallaCompacta?.removeEventListener('change', actualizarVistaCompacta))

function actualizarVistaCompacta(evento) {
  vistaCompacta.value = evento.matches
  if (!evento.matches) detalleEnDialogo.value = false
}

async function consultar({ preservarSeleccion = false } = {}) {
  const canchas = [...props.canchas]
  if (!canchas.length) {
    bloquesPorCancha.value = {}
    consultado.value = false
    return
  }

  const consultaId = ++solicitudConsulta
  const seleccionAnterior = preservarSeleccion ? [...seleccion.value] : []
  const { desde, hasta } = rango.value
  cargando.value = true
  consultado.value = true
  error.value = ''
  solicitudCotizacion += 1
  cotizando.value = false
  if (!preservarSeleccion) {
    bloquesPorCancha.value = {}
    seleccion.value = []
    errorSeleccion.value = ''
  }
  detalle.value = null
  detalleEnDialogo.value = false
  cotizacion.value = null

  try {
    const resultados = await Promise.allSettled(canchas.map(async (cancha) => {
      const { data } = await reservasApi.disponibilidadAdministracion(cancha.id, desde, hasta)
      if (data?.considera_reservas !== true) throw new Error('Respuesta de disponibilidad no válida.')
      return {
        id: String(cancha.id),
        bloques: Array.isArray(data.bloques) ? data.bloques : [],
        zonaHoraria: data.zona_horaria || 'America/Lima',
      }
    }))
    if (consultaId !== solicitudConsulta) return

    const cargados = resultados.filter((resultado) => resultado.status === 'fulfilled').map((resultado) => resultado.value)
    bloquesPorCancha.value = Object.fromEntries(cargados.map((resultado) => [resultado.id, resultado]))
    if (cargados.length) zonaHoraria.value = cargados[0].zonaHoraria
    const fallidos = resultados.length - cargados.length
    if (fallidos) error.value = `No se pudo consultar el horario de ${fallidos} ${fallidos === 1 ? 'cancha' : 'canchas'}. Actualiza la consulta para volver a intentarlo.`
    else tiempoReal.marcarConsultaExitosa()
    if (preservarSeleccion && seleccionAnterior.length) {
      const actualizada = seleccionAnterior.map((anterior) => {
        const datos = bloquesPorCancha.value[anterior.canchaId]
        const bloque = datos?.bloques.find((item) => item.fecha_inicio === anterior.fecha_inicio)
        if (!datos || !bloque) return null
        return bloquePuedeCotizar(bloque) && !bloque.estado_reserva
          ? { ...bloque, canchaId: anterior.canchaId, canchaNombre: anterior.canchaNombre,
            zonaHoraria: datos.zonaHoraria }
          : null
      })
      if (actualizada.some((bloque) => !bloque)) {
        seleccion.value = []
        errorSeleccion.value = fallidos
          ? 'No se pudo verificar tu selección. Actualiza el calendario antes de elegir nuevamente.'
          : 'El horario seleccionado dejó de estar disponible. Elige otro bloque.'
      } else {
        seleccion.value = actualizada
        errorSeleccion.value = ''
      }
    }
  } catch (fallo) {
    if (consultaId === solicitudConsulta) {
      error.value = mensajeErrorApi(fallo, 'No se pudieron cargar los horarios operativos.')
      bloquesPorCancha.value = {}
      if (preservarSeleccion && seleccionAnterior.length) {
        seleccion.value = []
        errorSeleccion.value = 'No se pudo verificar tu selección. Actualiza el calendario antes de elegir nuevamente.'
      }
    }
  } finally {
    if (consultaId === solicitudConsulta) cargando.value = false
  }
}

function navegar(direccion) {
  const nuevaFecha = desplazarFecha(fecha.value, direccion * (vista.value === 'dia' ? 1 : 7))
  fecha.value = nuevaFecha
  if (vista.value === 'dia') fechaActiva.value = nuevaFecha
}

function irAHoy() {
  const hoy = fechaActualLima()
  fecha.value = hoy
  fechaActiva.value = hoy
}

function cambiarDia(dia) { fechaActiva.value = dia }

function verDetalle(bloque) {
  detalle.value = bloque
  detalleEnDialogo.value = vistaCompacta.value
}

function seleccionarBloque({ canchaId, canchaNombre, bloque }) {
  const nuevo = { ...bloque, canchaId, canchaNombre, zonaHoraria: zonaHoraria.value }
  solicitudCotizacion += 1
  cotizando.value = false
  detalle.value = nuevo
  errorSeleccion.value = ''
  cotizacion.value = null

  const mismaCancha = seleccion.value[0]?.canchaId === canchaId
  if (seleccion.value.length && !mismaCancha) {
    seleccion.value = [nuevo]
    return
  }

  const indice = seleccion.value.findIndex((item) => item.fecha_inicio === bloque.fecha_inicio)
  if (indice >= 0) {
    if (seleccion.value.length === 1) seleccion.value = []
    else if (indice === 0) seleccion.value = seleccion.value.slice(1)
    else if (indice === seleccion.value.length - 1) seleccion.value = seleccion.value.slice(0, -1)
    else seleccion.value = [nuevo]
    return
  }

  if (seleccion.value.length >= 24) {
    errorSeleccion.value = 'La cotización admite hasta 24 bloques consecutivos.'
    return
  }
  const primera = seleccion.value[0]
  const ultima = seleccion.value[seleccion.value.length - 1]
  if (!seleccion.value.length || Date.parse(ultima.fecha_fin) === Date.parse(bloque.fecha_inicio)) {
    seleccion.value = [...seleccion.value, nuevo]
  } else if (Date.parse(bloque.fecha_fin) === Date.parse(primera.fecha_inicio)) {
    seleccion.value = [nuevo, ...seleccion.value]
  } else {
    seleccion.value = [nuevo]
  }
}

function limpiarSeleccion() {
  solicitudCotizacion += 1
  cotizando.value = false
  seleccion.value = []
  cotizacion.value = null
  errorSeleccion.value = ''
}

async function cotizar() {
  if (!seleccion.value.length || !seleccion.value[0].canchaId) return
  const actual = ++solicitudCotizacion
  cotizando.value = true
  errorSeleccion.value = ''
  cotizacion.value = null
  const primero = seleccion.value[0]
  try {
    const { data } = await tarifasApi.calcular(primero.canchaId, {
      fecha: primero.fecha_inicio.slice(0, 10),
      hora_inicio: horaLocalISO(primero.fecha_inicio),
      duracion_horas: seleccion.value.length,
    })
    if (actual === solicitudCotizacion) cotizacion.value = data
  } catch (fallo) {
    if (actual === solicitudCotizacion) errorSeleccion.value = mensajeErrorApi(fallo, 'No se pudo calcular esta cotización preliminar.')
  } finally { if (actual === solicitudCotizacion) cotizando.value = false }
}

function etiquetaRango() {
  return vista.value === 'dia'
    ? fechaTitulo.value
    : `${fechaEtiqueta(rango.value.desde)} – ${fechaEtiqueta(rango.value.hasta)}`
}
</script>

<template>
  <section class="calendar-admin-view" aria-label="Calendario de canchas">
    <SelectorPeriodoCalendario v-model:vista="vista" v-model:fecha="fecha" :fecha-activa="fechaActiva"
      :dias="dias" :titulo="vista === 'dia' ? fechaTitulo : etiquetaRango()" @navegar="navegar"
      @hoy="irAHoy" @cambiar-dia="cambiarDia" />

    <div class="calendar-context-row">
      <div class="calendar-facility-filter">
        <Grid2X2 aria-hidden="true" />
        <span>Todas las canchas de la sede</span>
        <strong>{{ canchas.length }}</strong>
      </div>
      <span class="calendar-timezone"><CalendarClock aria-hidden="true" />{{ zonaHoraria }}</span>
    </div>

    <EstadoDisponibilidadTiempoReal :estado="tiempoReal.estado.value"
      :sincronizado-en="tiempoReal.sincronizadoEn.value" :cargando="cargando" @actualizar="consultar" />

    <div class="calendar-caveat" role="note">
      <Info aria-hidden="true" />
      <p>Este calendario integra horarios, tarifas y retenciones. <strong>Una retención aparta el bloque temporalmente, pero no registra un pago ni confirma la reserva.</strong></p>
    </div>

    <div class="calendar-stats-grid" aria-label="Resumen de bloques del día" aria-live="polite">
      <TarjetaResumenCalendario v-for="tarjeta in tarjetasEstadistica" :key="tarjeta.id" v-bind="tarjeta" />
    </div>

    <p v-if="error" class="admin-error" role="alert">{{ error }} <BotonBase variante="texto" tamano="pequeno" @click="consultar"><template #icono-inicio><RefreshCw aria-hidden="true" /></template>Actualizar</BotonBase></p>
    <p v-if="cargando" class="admin-card calendar-loading" role="status" aria-live="polite">Consultando horarios y tarifas de las canchas…</p>

    <div class="calendar-content-grid">
      <section v-if="!cargando && consultado && !horas.length" class="admin-card calendar-empty-state" role="status">
        <CalendarDays aria-hidden="true" />
        <h2>No hay bloques operativos para esta fecha</h2>
        <p>Prueba otra fecha o revisa los horarios configurados para esta sede.</p>
      </section>
      <MatrizHorarioCanchas v-else-if="!cargando && horas.length" :filas="filas" :horas="horas" :zona-horaria="zonaHoraria" :seleccion="seleccion" @seleccionar="seleccionarBloque" @detalle="verDetalle" />
      <ResumenCalendarioLateral :detalle="detalle" :seleccion="seleccion" :cotizacion="cotizacion" :cotizando="cotizando" :error="errorSeleccion" :zona-horaria="zonaHoraria" @cotizar="cotizar" @limpiar="limpiarSeleccion" />
    </div>

    <DialogoDetalleHorario v-if="detalle" v-model="detalleEnDialogo" :detalle="detalle" :zona-horaria="zonaHoraria" />
  </section>
</template>

<style scoped>
.calendar-admin-view { display: grid; gap: 18px; min-width: 0; }
.calendar-context-row { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 10px; }
.calendar-facility-filter, .calendar-timezone { display: inline-flex; min-height: 40px; align-items: center; gap: 9px; border: 1px solid var(--border); border-radius: 999px; background: var(--surface-2); padding: 7px 12px; color: var(--text-muted); font-size: 13px; font-weight: 600; }
.calendar-facility-filter svg, .calendar-timezone svg { height: 16px; width: 16px; color: var(--link); }
.calendar-facility-filter strong { display: grid; min-width: 24px; height: 24px; place-items: center; border-radius: 999px; background: var(--surface-3); color: var(--text); font-size: 12px; }
.calendar-timezone { background: var(--surface); font-variant-numeric: tabular-nums; }
.calendar-caveat { display: flex; align-items: flex-start; gap: 10px; border: 1px solid color-mix(in srgb, var(--status-info-text) 28%, var(--border)); border-radius: var(--radius-md); background: var(--status-info-bg); padding: 12px 14px; color: var(--status-info-text); }
.calendar-caveat svg { height: 18px; width: 18px; flex: 0 0 auto; margin-top: 1px; }
.calendar-caveat p { margin: 0; font-size: 13px; line-height: 1.5; }
.calendar-stats-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; }
.calendar-content-grid { display: grid; min-width: 0; grid-template-columns: minmax(0, 1fr) minmax(290px, 340px); align-items: start; gap: 16px; }
.calendar-empty-state { min-height: 280px; display: grid; align-content: center; justify-items: center; text-align: center; }
.calendar-empty-state > svg { height: 28px; width: 28px; color: var(--text-muted); }
.calendar-empty-state h2 { margin: 12px 0 0; font: 700 18px/1.35 var(--font-body); }
.calendar-empty-state p { margin: 6px 0 0; color: var(--text-muted); font-size: 14px; }
.calendar-loading { color: var(--text-muted); }
@media (max-width: 1279px) {
  .calendar-content-grid { grid-template-columns: minmax(0, 1fr) 300px; }
}
@media (max-width: 1023px) {
  .calendar-content-grid { grid-template-columns: minmax(0, 1fr); }
  .calendar-stats-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 639px) {
  .calendar-admin-view { gap: 14px; }
  .calendar-context-row { align-items: flex-start; flex-direction: column; }
  .calendar-stats-grid { gap: 8px; }
}
</style>
