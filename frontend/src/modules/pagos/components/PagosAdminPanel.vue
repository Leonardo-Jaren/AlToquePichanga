<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { BadgeCheck, ClipboardList, Search, Settings2 } from 'lucide-vue-next'
import api from '@/shared/services/api'
import BotonBase from '@/shared/components/BotonBase.vue'
import ModalBase from '@/shared/components/ModalBase.vue'
import TablaBase from '@/shared/components/TablaBase.vue'
import MetodoPagoFormulario from './MetodoPagoFormulario.vue'
import RevisionPagoModal from './RevisionPagoModal.vue'
import { pagosApi } from '../services/pagos'
import { fechaPago, soles, etiquetaEstadoPago } from '../utils/pagos'

const props = defineProps({
  sedes: { type: Array, default: () => [] },
  sedeInicialId: { type: [String, Number], default: null },
  sedeFija: { type: Boolean, default: false },
  configurarMedios: { type: Boolean, default: false },
  cargarSedes: { type: Boolean, default: false },
})
const columnas = [
  { key: 'codigo', label: 'Reserva' }, { key: 'jugador', label: 'Jugador' },
  { key: 'sede', label: 'Sede / cancha' }, { key: 'metodo', label: 'Medio' },
  { key: 'importe', label: 'Importe' }, { key: 'estado', label: 'Estado' },
  { key: 'creado', label: 'Fecha' }, { key: 'acciones', label: 'Revisión' },
]
const estados = [
  { value: '', label: 'Todos los estados' },
  { value: 'pendiente_revision', label: 'Por revisar' },
  { value: 'pendiente_pago', label: 'Pendiente de pago' },
  { value: 'aprobado', label: 'Aprobado' },
  { value: 'rechazado', label: 'Rechazado' },
  { value: 'vencido', label: 'Vencido' },
  { value: 'pago_tardio', label: 'Pago tardío' },
]
const sedesLocales = ref([])
const sedeId = ref(props.sedeInicialId ? String(props.sedeInicialId) : '')
const cargando = ref(false)
const cargandoMedios = ref(false)
const guardandoRevision = ref(false)
const error = ref('')
const aviso = ref('')
const pagos = ref([])
const medios = ref([])
const estado = ref('pendiente_revision')
const busqueda = ref('')
const desde = ref('')
const hasta = ref('')
const seleccion = ref(null)
const modal = ref(false)
const medioEditor = ref(null)
const disponibles = computed(() => props.sedes.length ? props.sedes : sedesLocales.value)
const nombreSede = computed(() => disponibles.value.find((sede) => String(sede.id) === String(sedeId.value))?.nombre || '')
const mediosConfigurables = computed(() => medios.value.filter((medio) => ['yape', 'plin', 'transferencia'].includes(medio.tipo)))
const tarjetasMedio = computed(() => ['yape', 'plin', 'transferencia'].map((tipo) => ({
  tipo, metodo: mediosConfigurables.value.find((medio) => medio.tipo === tipo) || null,
})))
const filtroSedeBloqueado = computed(() => props.sedeFija && Boolean(props.sedeInicialId))

onMounted(async () => {
  if (props.cargarSedes) {
    try { sedesLocales.value = (await api.get('/sedes/')).data }
    catch { error.value = 'No se pudieron cargar las sedes autorizadas.' }
  }
  if (!sedeId.value && disponibles.value.length === 1) sedeId.value = String(disponibles.value[0].id)
  await cargar()
})
watch(() => props.sedeInicialId, async (valor) => {
  if (valor) { sedeId.value = String(valor); await cargar() }
})
watch(() => props.sedes, async (lista) => {
  if (!sedeId.value && lista.length === 1) sedeId.value = String(lista[0].id)
  await cargar()
})
watch(sedeId, cargarMedios)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await pagosApi.listarAdministracion({
      ...(sedeId.value ? { sede: Number(sedeId.value) } : {}),
      ...(estado.value ? { estado: estado.value } : {}),
      ...(busqueda.value.trim() ? { q: busqueda.value.trim() } : {}),
      ...(desde.value ? { desde: desde.value } : {}),
      ...(hasta.value ? { hasta: hasta.value } : {}),
    })
    pagos.value = data.results || []
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudieron cargar los pagos de tus sedes.'
    pagos.value = []
  } finally { cargando.value = false }
}

async function cargarMedios() {
  medios.value = []
  if (!sedeId.value) return
  cargandoMedios.value = true
  try { medios.value = (await pagosApi.listarMedios(Number(sedeId.value))).data }
  catch (fallo) { error.value = fallo.response?.data?.detail || 'No se pudieron cargar los medios de pago.' }
  finally { cargandoMedios.value = false }
}

async function abrir(pago) {
  error.value = ''
  modal.value = true
  try { seleccion.value = (await pagosApi.detalleAdministracion(pago.id)).data }
  catch (fallo) { modal.value = false; error.value = fallo.response?.data?.detail || 'No se pudo abrir el pago.' }
}

async function revisar(accion, datos) {
  if (!seleccion.value || guardandoRevision.value) return
  guardandoRevision.value = true
  error.value = ''
  aviso.value = ''
  try {
    const { data } = accion === 'aprobar'
      ? await pagosApi.aprobar(seleccion.value.id, datos)
      : await pagosApi.rechazar(seleccion.value.id, datos)
    seleccion.value = data
    aviso.value = accion === 'aprobar'
      ? 'Pago verificado. La reserva queda pendiente de confirmación.'
      : 'Comprobante rechazado. El historial conserva el motivo.'
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo guardar la revisión.'
    if (seleccion.value) {
      try { seleccion.value = (await pagosApi.detalleAdministracion(seleccion.value.id)).data } catch { /* conserva el detalle previo */ }
    }
  } finally { guardandoRevision.value = false }
}

function mostrarMedio(tipo) {
  return { yape: 'Yape', plin: 'Plin', transferencia: 'Transferencia' }[tipo] || tipo
}

function editarMedio(tipo) {
  medioEditor.value = {
    tipo,
    metodo: mediosConfigurables.value.find((medio) => medio.tipo === tipo) || null,
  }
}

function medioGuardado() {
  medioEditor.value = null
  cargarMedios()
}
</script>

<template>
  <div class="pagos-admin">
    <div class="pagos-admin-intro">
      <div class="pagos-admin-marca"><ClipboardList aria-hidden="true" /></div>
      <div><p class="pagos-eyebrow">Pagos de reservas</p><h2>Comprobantes y revisión</h2><p>Revisa cada pago contra los movimientos de la cuenta de la sede. WhatsApp solo transporta la captura.</p></div>
    </div>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="aviso" role="status" class="admin-success"><BadgeCheck aria-hidden="true" class="size-4" />{{ aviso }}</p>

    <section class="pagos-filtros admin-card" aria-label="Filtros de pagos">
      <label v-if="disponibles.length > 1 && !filtroSedeBloqueado" class="filtro-sede"><span class="admin-label">Sede</span><select v-model="sedeId" class="admin-field"><option value="">Todas tus sedes autorizadas</option><option v-for="sede in disponibles" :key="sede.id" :value="String(sede.id)">{{ sede.nombre }}</option></select></label>
      <label><span class="admin-label">Estado</span><select v-model="estado" class="admin-field"><option v-for="item in estados" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
      <label class="busqueda-pago"><span class="admin-label">Código o jugador</span><span class="campo-busqueda"><Search aria-hidden="true" /><input v-model.trim="busqueda" class="admin-field" placeholder="Ej. ATP-… o correo" @keyup.enter="cargar"></span></label>
      <label><span class="admin-label">Desde</span><input v-model="desde" class="admin-field" type="date"></label>
      <label><span class="admin-label">Hasta</span><input v-model="hasta" class="admin-field" type="date"></label>
      <BotonBase class="boton-filtro" :cargando="cargando" @click="cargar"><template #icono-inicio><Search aria-hidden="true" /></template>Aplicar filtros</BotonBase>
    </section>

    <section class="admin-card tabla-pagos" aria-label="Cola de revisión">
      <div class="tabla-pagos-heading"><div><h3>Cola de revisión</h3><p>{{ pagos.length }} resultados · máximo 100 por consulta</p></div><BotonBase variante="secundario" :deshabilitado="cargando" @click="cargar">Actualizar</BotonBase></div>
      <TablaBase :columnas="columnas" :filas="pagos" clave="id" :cargando="cargando" vacio="No hay pagos para estos filtros." etiqueta="Pagos de reserva">
        <template #celda-codigo="{ fila }"><strong class="codigo-pago">{{ fila.codigo_reserva }}</strong></template>
        <template #celda-jugador="{ fila }"><span>{{ fila.jugador.nombre }}</span><small class="dato-secundario">{{ fila.jugador.correo }}</small></template>
        <template #celda-sede="{ fila }"><span>{{ fila.sede }}</span><small class="dato-secundario">{{ fila.cancha }}</small></template>
        <template #celda-metodo="{ fila }">{{ mostrarMedio(fila.metodo.tipo) }}</template>
        <template #celda-importe="{ fila }"><strong>{{ soles(fila.importe_verificado && fila.estado === 'aprobado' ? fila.importe_verificado : fila.importe_solicitado) }}</strong></template>
        <template #celda-estado="{ fila }"><span :class="['etiqueta-pago', `etiqueta-${fila.estado}`]">{{ etiquetaEstadoPago(fila.estado) }}</span><small v-if="fila.requiere_conciliacion" class="dato-incidencia">Conciliación requerida</small></template>
        <template #celda-creado="{ fila }">{{ fechaPago(fila.creado_en) }}</template>
        <template #celda-acciones="{ fila }"><BotonBase tamano="pequeno" @click="abrir(fila)">{{ fila.estado === 'pendiente_revision' ? 'Revisar' : 'Detalle' }}</BotonBase></template>
      </TablaBase>
    </section>

    <section v-if="configurarMedios" class="config-medios">
      <header class="config-medios-heading"><div class="config-medios-icono"><Settings2 aria-hidden="true" /></div><div><p class="pagos-eyebrow">Datos visibles al jugador</p><h2>Medios de pago de {{ nombreSede || 'la sede' }}</h2><p>Usa cuentas propias de esta sede. El dinero de las reservas no pasa por AlToque.</p></div></header>
      <label v-if="disponibles.length > 1 && !sedeFija" class="max-w-md"><span class="admin-label">Configurar sede</span><select v-model="sedeId" class="admin-field"><option v-for="sede in disponibles" :key="sede.id" :value="String(sede.id)">{{ sede.nombre }}</option></select></label>
      <div v-if="cargandoMedios" role="status" class="admin-card">Cargando medios de pago…</div>
      <div v-else-if="sedeId" class="medios-grid">
        <article v-for="tarjeta in tarjetasMedio" :key="`${sedeId}-${tarjeta.tipo}`" class="medio-resumen">
          <div class="medio-resumen-cabecera">
            <div><p class="pagos-eyebrow">{{ tarjeta.tipo === 'transferencia' ? 'Cuenta bancaria' : 'Billetera digital' }}</p><h3>{{ mostrarMedio(tarjeta.tipo) }}</h3></div>
            <span :class="['medio-estado', tarjeta.metodo?.activo ? 'medio-estado-visible' : '']">
              {{ tarjeta.metodo?.activo ? 'Visible' : tarjeta.metodo ? 'Pausado' : 'Sin configurar' }}
            </span>
          </div>
          <p class="medio-titular">{{ tarjeta.metodo?.titular || 'Agrega los datos que verá el jugador.' }}</p>
          <small v-if="tarjeta.metodo?.numero_cuenta" class="medio-numero">{{ tarjeta.metodo.numero_cuenta }}</small>
          <BotonBase variante="secundario" class="medio-editar" @click="editarMedio(tarjeta.tipo)">
            {{ tarjeta.metodo ? `Editar ${mostrarMedio(tarjeta.tipo)}` : `Configurar ${mostrarMedio(tarjeta.tipo)}` }}
          </BotonBase>
        </article>
      </div>
      <div v-else class="admin-card"><p>Selecciona una sede para configurar sus cuentas.</p></div>
      <p class="nota-whatsapp">El número oficial de WhatsApp se administra en la información de contacto de la sede. Verifica que esté actualizado antes de habilitar los pagos.</p>
    </section>
    <section v-else class="aviso-sin-config"><p>Solo los dueños y administradores de sede pueden editar las cuentas. El equipo autorizado puede consultar y revisar los comprobantes.</p></section>

    <RevisionPagoModal v-model="modal" :pago="seleccion" :ocupado="guardandoRevision" @aprobar="revisar('aprobar', $event)" @rechazar="revisar('rechazar', $event)" />
    <ModalBase
      :model-value="Boolean(medioEditor)"
      :titulo="`${medioEditor?.metodo ? 'Editar' : 'Configurar'} ${mostrarMedio(medioEditor?.tipo || '')}`"
      descripcion="Estos datos aparecerán para el jugador en el pago de su reserva."
      ancho="mediano"
      @update:model-value="medioEditor = null"
    >
      <MetodoPagoFormulario
        v-if="medioEditor"
        :key="`${sedeId}-${medioEditor.tipo}`"
        :sede-id="Number(sedeId)"
        :tipo="medioEditor.tipo"
        :metodo="medioEditor.metodo"
        @guardado="medioGuardado"
      />
      <template #pie>
        <BotonBase variante="secundario" @click="medioEditor = null">Cancelar</BotonBase>
      </template>
    </ModalBase>
  </div>
</template>

<style scoped>
.pagos-admin { display: grid; gap: 18px; }
.pagos-admin-intro,.config-medios-heading { display: flex; align-items: flex-start; gap: 14px; }
.pagos-admin-marca,.config-medios-icono { display: grid; width: 42px; height: 42px; place-items: center; flex: 0 0 auto; border-radius: 12px; background: var(--selection-bg); color: var(--link); }
.pagos-admin-marca svg,.config-medios-icono svg { width: 20px; height: 20px; }
.pagos-eyebrow { margin: 0 0 4px; color: var(--link); font-size: 10px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }
.pagos-admin-intro h2,.config-medios-heading h2 { margin: 0; font: 700 21px/1.3 var(--font-body); }
.pagos-admin-intro p:last-child,.config-medios-heading p:last-child { margin: 4px 0 0; color: var(--text-muted); font-size: 13px; line-height: 1.4; }
.pagos-filtros { display: grid; grid-template-columns: minmax(150px,1fr) minmax(170px,1.2fr) minmax(150px,.8fr) minmax(150px,.8fr) auto; align-items: end; gap: 10px; }
.busqueda-pago { grid-column: span 2; }
.admin-label { display: block; margin-bottom: 4px; font-size: 11px; font-weight: 600; }
.admin-field { width: 100%; min-height: 42px; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); padding: 8px 10px; color: var(--text); font: 13px var(--font-body); }
.admin-field:focus-visible { outline: 3px solid var(--brand-lime); outline-offset: 2px; }
.campo-busqueda { position: relative; display: block; }
.campo-busqueda svg { position: absolute; top: 12px; left: 11px; width: 16px; height: 16px; color: var(--text-muted); }
.campo-busqueda input { padding-left: 34px; }
.boton-filtro { grid-column: -2 / -1; }
.tabla-pagos { display: grid; gap: 13px; }
.tabla-pagos-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.tabla-pagos-heading h3 { margin: 0; font-size: 16px; }
.tabla-pagos-heading p { margin: 3px 0 0; color: var(--text-muted); font-size: 11px; }
.codigo-pago { color: var(--link); font: 700 11px ui-monospace,monospace; white-space: nowrap; }
.dato-secundario { display: block; margin-top: 3px; color: var(--text-muted); font-size: 10px; }
.dato-incidencia { display: block; margin-top: 5px; color: var(--danger); font-size: 10px; font-weight: 700; }
.etiqueta-pago { display: inline-flex; width: max-content; max-width: 160px; border-radius: 999px; background: var(--surface-2); padding: 5px 7px; color: var(--text-muted); font-size: 10px; font-weight: 700; line-height: 1.2; }
.etiqueta-pendiente_revision,.etiqueta-pendiente_pago { background: var(--warning-bg); color: var(--warning); }
.etiqueta-aprobado { background: var(--success-bg); color: var(--success); }
.etiqueta-rechazado,.etiqueta-pago_tardio { background: var(--danger-bg); color: var(--danger); }
.config-medios { display: grid; gap: 14px; border-top: 1px solid var(--border); padding-top: 20px; }
.medios-grid { display: grid; grid-template-columns: repeat(3,minmax(0,1fr)); align-items: start; gap: 12px; }
.medio-resumen { display: grid; min-height: 174px; align-content: start; gap: 12px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 16px; box-shadow: var(--shadow); }
.medio-resumen-cabecera { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
.medio-resumen-cabecera h3 { margin: 0; font-size: 16px; }
.medio-resumen-cabecera .pagos-eyebrow { margin-bottom: 3px; font-size: 9px; }
.medio-estado { flex: 0 0 auto; border-radius: 999px; background: var(--surface-2); padding: 5px 8px; color: var(--text-muted); font-size: 10px; font-weight: 700; }
.medio-estado-visible { background: var(--success-bg); color: var(--success); }
.medio-titular { min-height: 20px; margin: 0; font-size: 13px; font-weight: 600; }
.medio-numero { color: var(--text-muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.medio-editar { justify-self: start; margin-top: auto; }
.nota-whatsapp,.aviso-sin-config { margin: 0; border-radius: var(--radius-md); background: var(--surface-2); padding: 11px 13px; color: var(--text-muted); font-size: 11px; line-height: 1.45; }
.admin-error,.admin-success { display: flex; align-items: center; gap: 6px; margin: 0; border-radius: 8px; padding: 9px 11px; font-size: 12px; }
.admin-error { background: var(--danger-bg); color: var(--danger); }
.admin-success { background: var(--success-bg); color: var(--success); }
.admin-card { border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 16px; box-shadow: var(--shadow); }
@media (max-width: 1020px) { .pagos-filtros { grid-template-columns: repeat(2,minmax(0,1fr)); } .busqueda-pago { grid-column: span 2; } .boton-filtro { grid-column: auto; } .medios-grid { grid-template-columns: 1fr 1fr; } }
@media (max-width: 640px) { .pagos-filtros { grid-template-columns: 1fr; } .busqueda-pago { grid-column: auto; } .medios-grid { grid-template-columns: 1fr; } .pagos-admin-intro h2,.config-medios-heading h2 { font-size: 18px; } .tabla-pagos-heading { align-items: flex-start; } }
</style>
