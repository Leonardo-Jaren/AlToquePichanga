<script setup>
import { computed, ref, watch } from 'vue'
import { CalendarDays, ChevronLeft, ChevronRight, Info, RotateCcw } from 'lucide-vue-next'
import { useAutenticacionStore } from '@/modules/autenticacion/stores/autenticacion'
import { horariosApi } from '@/modules/horarios/services/horarios'
import { tarifasApi } from '@/modules/tarifas/services/tarifas'
import { formatearPEN, mensajeErrorApi } from '@/modules/tarifas/utils/tarifas'
import SolicitudRetencionModal from '@/modules/reservas/components/SolicitudRetencionModal.vue'
import { calcularAdelantoMinimo } from '@/modules/reservas/utils/reservas'
import { useDisponibilidadTiempoReal } from '../../composables/useDisponibilidadTiempoReal'
import BloqueCalendario from '../bloques/BloqueCalendario.vue'
import EstadoDisponibilidadTiempoReal from './EstadoDisponibilidadTiempoReal.vue'
import { desplazarFecha, diasEntre, fechaActualLima, fechaEtiqueta, horaEtiqueta, horaLocalISO, rangoCalendario } from '../../utils/fechas'

const props = defineProps({
  cancha: { type: Object, required: true },
  publico: { type: Boolean, default: false },
})
const auth = useAutenticacionStore()

const vista = ref('dia')
const fecha = ref(fechaActualLima())
const bloques = ref([])
const zonaHoraria = ref('America/Lima')
const cargando = ref(false)
const cotizando = ref(false)
const consultado = ref(false)
const error = ref('')
const errorSeleccion = ref('')
const errorReserva = ref('')
const seleccion = ref([])
const detalle = ref(null)
const cotizacion = ref(null)
const solicitudAbierta = ref(false)
const rango = computed(() => rangoCalendario(vista.value, fecha.value))
const dias = computed(() => diasEntre(rango.value.desde, rango.value.hasta))
const grupos = computed(() => dias.value.map((dia) => ({
  fecha: dia,
  bloques: bloques.value.filter((bloque) => bloque.fecha_inicio?.slice(0, 10) === dia),
})))
const etiquetasRango = computed(() => vista.value === 'dia'
  ? fechaEtiqueta(fecha.value, { completa: true })
  : `${fechaEtiqueta(rango.value.desde)} – ${fechaEtiqueta(rango.value.hasta)}`)
const primeraSeleccion = computed(() => seleccion.value[0] || null)
const ultimaSeleccion = computed(() => seleccion.value[seleccion.value.length - 1] || null)
let solicitudConsulta = 0
let solicitudCotizacion = 0

const tiempoReal = useDisponibilidadTiempoReal({
  canchas: computed(() => props.publico && props.cancha?.id ? [props.cancha.id] : []),
  desde: computed(() => rango.value.desde),
  hasta: computed(() => rango.value.hasta),
  alCambiar: () => { void consultar({ preservarSeleccion: true }) },
  alRecuperar: () => { void consultar({ preservarSeleccion: true }) },
})

watch([() => props.cancha?.id, vista, fecha], () => consultar(), { immediate: true })

async function consultar({ preservarSeleccion = false } = {}) {
  if (!props.cancha?.id) return
  const seleccionAnterior = preservarSeleccion ? [...seleccion.value] : []
  const solicitud = ++solicitudConsulta
  const { desde, hasta } = rango.value
  cargando.value = true
  consultado.value = true
  error.value = ''
  solicitudCotizacion += 1
  cotizando.value = false
  cotizacion.value = null
  if (!preservarSeleccion) {
    errorSeleccion.value = ''
    seleccion.value = []
    detalle.value = null
    cotizacion.value = null
  } else {
    errorSeleccion.value = ''
  }
  try {
    const respuesta = props.publico
      ? await horariosApi.disponibilidadPublica(props.cancha.id, desde, hasta)
      : await horariosApi.disponibilidad(props.cancha.id, desde, hasta)
    if (solicitud !== solicitudConsulta) return
    const data = respuesta.data || {}
    const consideraReservasEsperado = props.publico
    if (data.considera_reservas !== consideraReservasEsperado) {
      error.value = props.publico
        ? 'No se pudo confirmar la disponibilidad real. Inténtalo de nuevo.'
        : 'La consulta no confirmó que se trate de disponibilidad operativa.'
      bloques.value = []
      if (preservarSeleccion && seleccionAnterior.length) {
        seleccion.value = []
        errorSeleccion.value = 'No se pudo verificar el horario seleccionado. Actualiza la disponibilidad y elige nuevamente.'
      }
      return
    }
    zonaHoraria.value = data.zona_horaria || 'America/Lima'
    const nuevosBloques = Array.isArray(data.bloques) ? data.bloques : []
    bloques.value = nuevosBloques
    tiempoReal.marcarConsultaExitosa()
    if (preservarSeleccion && seleccionAnterior.length) {
      const seleccionActualizada = seleccionAnterior.map((anterior) => nuevosBloques.find(
        (bloque) => bloque.fecha_inicio === anterior.fecha_inicio,
      ))
      if (seleccionActualizada.some((bloque) => !bloque || bloque.reservable !== true)) {
        seleccion.value = []
        errorSeleccion.value = 'El horario que tenías seleccionado dejó de estar disponible. Elige otro bloque.'
      } else {
        seleccion.value = seleccionActualizada
        errorSeleccion.value = ''
      }
    }
  } catch (fallo) {
    if (solicitud !== solicitudConsulta) return
    error.value = mensajeErrorApi(fallo, 'No se pudieron cargar los horarios y precios.')
    bloques.value = []
    if (preservarSeleccion && seleccionAnterior.length) {
      seleccion.value = []
      errorSeleccion.value = 'No se pudo verificar el horario seleccionado. Actualiza la disponibilidad y elige nuevamente.'
    }
  } finally {
    if (solicitud === solicitudConsulta) cargando.value = false
  }
}

function navegar(direccion) {
  fecha.value = desplazarFecha(fecha.value, direccion * (vista.value === 'dia' ? 1 : 7))
}

function seleccionarBloque(bloque) {
  solicitudCotizacion += 1
  cotizando.value = false
  errorReserva.value = ''
  errorSeleccion.value = ''
  cotizacion.value = null
  const indice = seleccion.value.findIndex((item) => item.fecha_inicio === bloque.fecha_inicio)
  if (indice >= 0) {
    if (seleccion.value.length === 1) seleccion.value = []
    else if (indice === 0) seleccion.value = seleccion.value.slice(1)
    else if (indice === seleccion.value.length - 1) seleccion.value = seleccion.value.slice(0, -1)
    else seleccion.value = [bloque]
    return
  }

  if (seleccion.value.length >= 24) {
    errorSeleccion.value = 'La cotización admite hasta 24 bloques consecutivos.'
    return
  }
  const seUneAlFinal = ultimaSeleccion.value
    && Date.parse(ultimaSeleccion.value.fecha_fin) === Date.parse(bloque.fecha_inicio)
  const seUneAlInicio = primeraSeleccion.value
    && Date.parse(bloque.fecha_fin) === Date.parse(primeraSeleccion.value.fecha_inicio)
  if (!seleccion.value.length || seUneAlFinal) seleccion.value = [...seleccion.value, bloque]
  else if (seUneAlInicio) seleccion.value = [bloque, ...seleccion.value]
  else seleccion.value = [bloque]
}

function limpiarSeleccion() {
  solicitudCotizacion += 1
  cotizando.value = false
  seleccion.value = []
  cotizacion.value = null
  errorSeleccion.value = ''
}

function verDetalle(bloque) { detalle.value = bloque }

function retencionCreada() { void consultar() }

function conflictoDeReserva() {
  errorReserva.value = 'Ese horario acaba de ocuparse. El calendario se actualizó; elige otro bloque.'
  solicitudAbierta.value = false
  limpiarSeleccion()
  void consultar()
}

async function cotizar() {
  if (!primeraSeleccion.value || !seleccion.value.length) return
  const solicitud = ++solicitudCotizacion
  cotizando.value = true
  errorSeleccion.value = ''
  cotizacion.value = null
  const entrada = {
    fecha: primeraSeleccion.value.fecha_inicio.slice(0, 10),
    hora_inicio: horaLocalISO(primeraSeleccion.value.fecha_inicio),
    duracion_horas: seleccion.value.length,
  }
  try {
    const respuesta = props.publico
      ? await tarifasApi.cotizarPublico(props.cancha.id, entrada)
      : await tarifasApi.calcular(props.cancha.id, entrada)
    if (solicitud === solicitudCotizacion) cotizacion.value = respuesta.data
  } catch (fallo) {
    if (solicitud === solicitudCotizacion) {
      errorSeleccion.value = mensajeErrorApi(fallo, 'No se pudo calcular esta cotización preliminar.')
    }
  } finally { if (solicitud === solicitudCotizacion) cotizando.value = false }
}

function etiquetaTarifa(tipo) {
  return ({ diurna: 'Diurna', nocturna: 'Nocturna', fin_semana: 'Fin de semana', feriado: 'Feriado', especial: 'Especial' })[tipo] || tipo || 'Sin tarifa'
}
</script>

<template>
  <section class="space-y-4" aria-labelledby="calendario-titulo">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <p class="text-xs font-semibold uppercase tracking-[0.14em] text-app-link">{{ cancha.sede?.nombre || cancha.sede || 'Cancha seleccionada' }}</p>
        <h2 id="calendario-titulo" class="mt-1 font-display text-xl sm:text-2xl">{{ cancha.nombre }} · Calendario</h2>
        <p class="mt-1 text-sm text-app-text-muted">Consulta horarios operativos y precios por bloque.</p>
      </div>
      <span class="inline-flex items-center gap-2 rounded-full border border-app-border bg-app-surface-2 px-3 py-2 text-xs font-semibold">
        <CalendarDays aria-hidden="true" class="size-4" /> {{ zonaHoraria }}
      </span>
    </div>

    <div class="flex items-start gap-2 rounded-xl border border-[var(--status-info-text)]/30 bg-[var(--status-info-bg)] p-3 text-sm text-[var(--status-info-text)]" role="note">
      <Info aria-hidden="true" class="mt-0.5 size-4 shrink-0" />
      <p v-if="publico">La disponibilidad incluye retenciones vigentes. Al solicitar una reserva, el horario se aparta temporalmente; no se registra un pago ni se confirma la reserva.</p>
      <p v-else>Esta vista muestra disponibilidad operativa y <strong>no considera reservas de jugadores</strong>. No confirma que una hora esté libre para alquilar. La selección genera solo una cotización preliminar; no guarda ni bloquea horarios.</p>
    </div>

    <EstadoDisponibilidadTiempoReal v-if="publico" :estado="tiempoReal.estado.value"
      :sincronizado-en="tiempoReal.sincronizadoEn.value" :cargando="cargando" @actualizar="consultar" />

    <section class="rounded-2xl border border-app-border bg-app-surface p-4 shadow-[var(--shadow)] sm:p-5" aria-label="Controles del calendario">
      <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <label class="block min-w-0">
          <span class="mb-1 block text-sm font-semibold">Fecha de referencia</span>
          <input v-model="fecha" class="min-h-11 w-full rounded-xl border border-[var(--border-strong)] bg-[var(--input-bg)] px-3 text-[var(--text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--brand-lime)]" type="date" aria-label="Fecha del calendario">
        </label>
        <div class="flex flex-wrap items-end gap-3">
          <div class="inline-flex rounded-xl border border-app-border bg-app-surface-2 p-1" aria-label="Vista del calendario">
            <button v-for="opcion in [{ id: 'dia', etiqueta: 'Día' }, { id: 'semana', etiqueta: 'Semana' }]" :key="opcion.id" class="min-h-10 rounded-lg px-4 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--brand-lime)]" :class="vista === opcion.id ? 'bg-app-surface text-app-text shadow-sm' : 'text-app-text-muted'" type="button" :aria-pressed="vista === opcion.id" @click="vista = opcion.id">{{ opcion.etiqueta }}</button>
          </div>
          <div class="flex gap-2">
            <button class="grid size-11 place-items-center rounded-xl border border-app-border bg-app-surface text-app-text hover:bg-app-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--brand-lime)]" type="button" aria-label="Periodo anterior" @click="navegar(-1)"><ChevronLeft aria-hidden="true" class="size-5" /></button>
            <button class="grid size-11 place-items-center rounded-xl border border-app-border bg-app-surface text-app-text hover:bg-app-surface-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--brand-lime)]" type="button" aria-label="Periodo siguiente" @click="navegar(1)"><ChevronRight aria-hidden="true" class="size-5" /></button>
          </div>
        </div>
      </div>
      <div class="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-app-border pt-4">
        <p class="font-semibold capitalize">{{ etiquetasRango }}</p>
        <p class="text-xs text-app-text-muted">Estados acompañados de texto e iconos</p>
      </div>
    </section>

    <p v-if="error" class="rounded-xl bg-[var(--status-danger-bg)] p-4 text-sm font-medium text-[var(--status-danger-text)]" role="alert">{{ error }}</p>
    <p v-if="errorReserva" class="rounded-xl bg-[var(--status-warning-bg)] p-4 text-sm font-medium text-[var(--status-warning-text)]" role="alert">{{ errorReserva }}</p>
    <p v-if="errorSeleccion && !seleccion.length" class="rounded-xl bg-[var(--status-warning-bg)] p-4 text-sm font-medium text-[var(--status-warning-text)]" role="alert">{{ errorSeleccion }}</p>
    <p v-if="cargando" class="rounded-xl border border-app-border bg-app-surface p-5 text-sm text-app-text-muted" role="status" aria-live="polite">Consultando horario, cierres y tarifas…</p>
    <div v-else-if="consultado && !bloques.length && !error" class="rounded-2xl border border-app-border bg-app-surface p-6 text-center">
      <CalendarDays aria-hidden="true" class="mx-auto size-7 text-app-text-muted" />
      <h3 class="mt-3 font-semibold">No hay bloques operativos</h3>
      <p class="mt-1 text-sm text-app-text-muted">No se encontraron intervalos para {{ etiquetasRango }}.</p>
    </div>

    <div v-else-if="!cargando && grupos.some((grupo) => grupo.bloques.length)" class="grid min-w-0 grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-7" aria-label="Calendario por día">
      <section v-for="grupo in grupos" :key="grupo.fecha" class="min-w-0 rounded-2xl border border-app-border bg-app-surface p-3 shadow-[var(--shadow)]" :aria-label="fechaEtiqueta(grupo.fecha, { completa: true })">
        <header class="mb-3 min-h-12 border-b border-app-border pb-2">
          <h3 class="font-semibold capitalize">{{ fechaEtiqueta(grupo.fecha, { completa: vista === 'dia' }) }}</h3>
          <p class="text-xs text-app-text-muted">{{ grupo.bloques.length }} {{ grupo.bloques.length === 1 ? 'bloque' : 'bloques' }}</p>
        </header>
        <p v-if="!grupo.bloques.length" class="rounded-lg bg-app-surface-2 p-3 text-sm text-app-text-muted">Sin horario configurado.</p>
        <div v-else class="space-y-2">
          <BloqueCalendario v-for="bloque in grupo.bloques" :key="bloque.fecha_inicio" :bloque="bloque" :zona-horaria="zonaHoraria" :publico="publico" :seleccionado="seleccion.some((item) => item.fecha_inicio === bloque.fecha_inicio)" @detalle="verDetalle" @seleccionar="seleccionarBloque" />
        </div>
      </section>
    </div>

    <section v-if="detalle && !cargando" class="rounded-2xl border border-app-border bg-app-surface p-4" aria-live="polite" aria-label="Detalle del intervalo">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div><h3 class="font-semibold">Detalle del intervalo</h3><p class="mt-1 tabular-nums">{{ fechaEtiqueta(detalle.fecha_inicio.slice(0, 10), { completa: true }) }}, {{ horaEtiqueta(detalle.fecha_inicio, zonaHoraria) }}–{{ horaEtiqueta(detalle.fecha_fin, zonaHoraria) }}</p></div>
        <button class="min-h-11 rounded-xl border border-app-border px-3 text-sm font-semibold text-app-text" type="button" @click="detalle = null">Cerrar detalle</button>
      </div>
      <dl class="mt-3 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div><dt class="text-app-text-muted">Estado operativo</dt><dd class="font-semibold">{{ detalle.estado }}</dd></div>
        <div><dt class="text-app-text-muted">Tarifa</dt><dd class="font-semibold">{{ etiquetaTarifa(detalle.tipo_tarifa) }}</dd></div>
        <div><dt class="text-app-text-muted">Precio</dt><dd class="font-semibold">{{ detalle.precio ? formatearPEN(detalle.precio, detalle.moneda) : 'No disponible' }}</dd></div>
        <div><dt class="text-app-text-muted">Origen del horario</dt><dd class="font-semibold">{{ detalle.origen === 'ampliacion_excepcional' ? 'Ampliación excepcional' : 'Horario semanal' }}</dd></div>
        <div v-if="detalle.motivo" class="sm:col-span-2"><dt class="text-app-text-muted">Motivo</dt><dd class="break-words">{{ detalle.motivo }}</dd></div>
      </dl>
    </section>

    <section v-if="seleccion.length" class="rounded-2xl border border-brand-lime bg-app-surface p-4 shadow-[var(--shadow)] sm:p-5" :aria-label="publico ? 'Solicitud de reserva' : 'Cotización preliminar'">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div><p class="text-xs font-semibold uppercase tracking-wide text-app-link">{{ publico ? 'Horario por solicitar' : 'Simulación · sin reserva' }}</p><h3 class="mt-1 font-semibold">{{ seleccion.length }} {{ seleccion.length === 1 ? 'bloque seleccionado' : 'bloques consecutivos seleccionados' }}</h3><p class="mt-1 text-sm text-app-text-muted">{{ horaEtiqueta(primeraSeleccion.fecha_inicio, zonaHoraria) }}–{{ horaEtiqueta(ultimaSeleccion.fecha_fin, zonaHoraria) }} · {{ fechaEtiqueta(primeraSeleccion.fecha_inicio.slice(0, 10), { completa: true }) }}</p></div>
        <div class="flex flex-wrap gap-2">
          <button class="min-h-11 rounded-xl border border-app-border px-3 text-sm font-semibold text-app-text" type="button" @click="limpiarSeleccion"><RotateCcw aria-hidden="true" class="mr-1 inline size-4" />Limpiar</button>
          <button class="min-h-11 rounded-xl bg-[var(--brand-lime)] px-4 text-sm font-bold text-[var(--on-brand-lime)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--brand-lime)] disabled:cursor-wait disabled:opacity-60" type="button" :disabled="cotizando" @click="cotizar">{{ cotizando ? 'Calculando…' : cotizacion ? 'Actualizar precio' : publico ? 'Calcular importe' : 'Cotizar selección' }}</button>
        </div>
      </div>
      <p v-if="errorSeleccion" class="mt-3 rounded-lg bg-[var(--status-danger-bg)] p-3 text-sm text-[var(--status-danger-text)]" role="alert">{{ errorSeleccion }}</p>
      <div v-if="cotizacion" class="mt-4 border-t border-app-border pt-4" aria-live="polite">
        <div class="flex flex-wrap items-baseline justify-between gap-2"><p class="font-semibold">{{ publico ? 'Total de la reserva' : 'Total estimado' }}</p><p class="text-2xl font-bold tabular-nums">{{ formatearPEN(cotizacion.total, cotizacion.moneda) }}</p></div>
        <p v-if="publico" class="mt-2 text-sm text-app-text-muted">Adelanto mínimo (50%): <strong class="text-app-text">{{ formatearPEN(calcularAdelantoMinimo(cotizacion.total), cotizacion.moneda) }}</strong></p>
        <ul class="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          <li v-for="bloque in cotizacion.bloques" :key="bloque.fecha_inicio" class="rounded-xl border border-app-border bg-app-surface-2 p-3 text-sm"><span class="block font-semibold">{{ horaEtiqueta(bloque.fecha_inicio, zonaHoraria) }}–{{ horaEtiqueta(bloque.fecha_fin, zonaHoraria) }}</span><span class="text-app-text-muted">{{ bloque.nombre_tarifa }} · {{ formatearPEN(bloque.precio, bloque.moneda) }}</span></li>
        </ul>
        <button v-if="publico && auth.usuario" class="mt-4 min-h-11 w-full rounded-xl bg-[var(--brand-lime)] px-4 text-sm font-bold text-[var(--on-brand-lime)] focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-[var(--brand-lime)]" type="button" @click="solicitudAbierta = true">Solicitar reserva temporal</button>
        <RouterLink v-else-if="publico" to="/ingresar" class="mt-4 grid min-h-11 place-items-center rounded-xl bg-[var(--brand-lime)] px-4 text-sm font-bold text-[var(--on-brand-lime)]">Inicia sesión para reservar</RouterLink>
      </div>
    </section>
    <SolicitudRetencionModal v-if="publico" v-model="solicitudAbierta" :cancha="cancha" :seleccion="seleccion" :cotizacion="cotizacion" @reservada="retencionCreada" @conflicto="conflictoDeReserva" />
  </section>
</template>
