<script setup>
import { onMounted, reactive, ref } from 'vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { plataformaApi } from '@/modules/empresas/services/empresas'

const solicitudes = ref([])
const pagina = ref(1)
const cantidad = ref(0)
const estado = ref('pendiente')
const cargando = ref(false)
const procesando = ref(null)
const error = ref('')
const mensaje = ref('')
const decision = reactive({})
const hoy = new Date()
const fechaHoy = () => hoy.getFullYear() + '-' + String(hoy.getMonth() + 1).padStart(2, '0')
  + '-' + String(hoy.getDate()).padStart(2, '0')
const filtros = [['pendiente', 'Pendientes'], ['aprobada', 'Aprobadas'], ['rechazada', 'Rechazadas'], ['', 'Todas']]

onMounted(cargar)
function iniciar(request) {
  if (decision[request.id]) return
  let inicio = fechaHoy()
  if (request.suscripcion_actual?.vencimiento && request.suscripcion_actual.estado !== 'cancelada') {
    const fin = request.suscripcion_actual.vencimiento
    if (fin >= inicio) {
      const partes = fin.split('-').map(Number)
      const diaSiguiente = new Date(partes[0], partes[1] - 1, partes[2] + 1)
      inicio = diaSiguiente.getFullYear() + '-' + String(diaSiguiente.getMonth() + 1).padStart(2, '0')
        + '-' + String(diaSiguiente.getDate()).padStart(2, '0')
    }
  }
  decision[request.id] = {
    importe: request.precio, medio: request.medio_declarado || '',
    referencia: request.referencia_declarada || '', fecha_inicio: inicio,
  }
}
async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await plataformaApi.solicitudes({ page: pagina.value, estado: estado.value })
    solicitudes.value = data.results
    cantidad.value = data.count
    solicitudes.value.forEach(iniciar)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudieron cargar las solicitudes.'
  } finally { cargando.value = false }
}
async function cambiarFiltro() { pagina.value = 1; await cargar() }
async function resolver(request, aprobar) {
  if (aprobar && !window.confirm(
    'Confirma que verificaste manualmente el pago de ' + request.empresa + ' por ' + request.moneda + ' ' + request.precio + '.',
  )) return
  if (!aprobar && !window.confirm('¿Rechazar la solicitud de ' + request.empresa + '?')) return
  procesando.value = request.id
  error.value = ''
  mensaje.value = ''
  const form = decision[request.id]
  try {
    await plataformaApi.resolverSolicitud(request.id, {
      aprobar,
      ...(aprobar ? {
        importe_verificado: form.importe,
        referencia_verificada: form.referencia,
        medio_verificado: form.medio,
        fecha_inicio: form.fecha_inicio,
      } : {}),
    })
    mensaje.value = aprobar ? 'Solicitud aprobada; el periodo quedó registrado.' : 'Solicitud rechazada.'
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo resolver la solicitud.'
  } finally { procesando.value = null }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="solicitudes-titulo">
    <div>
      <h2 id="solicitudes-titulo" class="text-xl font-bold">Solicitudes de suscripción</h2>
      <p class="mt-1 text-sm text-app-text-muted">La solicitud y la referencia declarada no activan el servicio. Verifica el importe recibido antes de aprobar.</p>
    </div>
    <label class="block max-w-xs"><span class="admin-label">Estado</span><select v-model="estado" class="admin-field" @change="cambiarFiltro"><option v-for="opcion in filtros" :key="opcion[0]" :value="opcion[0]">{{ opcion[1] }}</option></select></label>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>
    <p v-if="cargando" role="status" class="text-sm text-app-text-muted">Cargando solicitudes…</p>
    <div v-else-if="!solicitudes.length" class="admin-card">
      <p class="font-semibold">No hay solicitudes en este estado.</p>
      <p class="mt-1 text-sm text-app-text-muted">Las nuevas solicitudes aparecerán aquí para revisión manual.</p>
    </div>
    <div v-else class="space-y-4">
      <article v-for="request in solicitudes" :key="request.id" class="admin-card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p class="text-sm text-app-text-muted">{{ request.tipo }} · Solicitud #{{ request.id }}</p>
            <h3 class="mt-1 text-lg font-bold">{{ request.empresa }}</h3>
            <p class="mt-1">{{ request.plan.nombre }} · {{ request.moneda }} {{ request.precio }} · {{ request.frecuencia }}</p>
          </div>
          <EstadoEtiqueta :estado="request.estado" />
        </div>
        <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div><dt class="text-app-text-muted">Solicitante</dt><dd>{{ request.solicitante || 'Propietario' }}</dd></div>
          <div><dt class="text-app-text-muted">Empresa</dt><dd>{{ request.estado_empresa }}</dd></div>
          <div><dt class="text-app-text-muted">Medio declarado</dt><dd>{{ request.medio_declarado || 'Sin medio declarado' }}</dd></div>
          <div><dt class="text-app-text-muted">Referencia declarada</dt><dd class="break-words">{{ request.referencia_declarada || 'Sin referencia' }}</dd></div>
          <div v-if="request.suscripcion_actual"><dt class="text-app-text-muted">Vencimiento actual</dt><dd>{{ request.suscripcion_actual.vencimiento || 'Sin periodo' }}</dd></div>
          <div v-if="request.nota"><dt class="text-app-text-muted">Nota</dt><dd class="break-words">{{ request.nota }}</dd></div>
        </dl>
        <form v-if="request.estado === 'pendiente'" class="mt-5 grid gap-4 border-t border-app-border pt-5 md:grid-cols-2" @submit.prevent="resolver(request, true)" :aria-busy="procesando === request.id">
          <label><span class="admin-label">Importe recibido</span><input v-model="decision[request.id].importe" class="admin-field" type="number" min="0" step="0.01" required></label>
          <label><span class="admin-label">Fecha de inicio del periodo</span><input v-model="decision[request.id].fecha_inicio" class="admin-field" type="date" required></label>
          <label><span class="admin-label">Medio verificado <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="decision[request.id].medio" class="admin-field" maxlength="40"></label>
          <label><span class="admin-label">Referencia verificada <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="decision[request.id].referencia" class="admin-field" maxlength="120"></label>
          <div class="flex flex-wrap gap-2 md:col-span-2">
            <button class="admin-button admin-button-primary" :disabled="procesando === request.id">{{ procesando === request.id ? 'Guardando…' : 'Confirmar pago y activar' }}</button>
            <button class="admin-button admin-button-danger" type="button" :disabled="procesando === request.id" @click="resolver(request, false)">Rechazar</button>
          </div>
        </form>
      </article>
      <div class="flex flex-wrap items-center justify-between gap-3 border-t border-app-border pt-4">
        <span class="text-sm text-app-text-muted">{{ cantidad }} solicitudes · página {{ pagina }}</span>
        <div class="flex gap-2">
          <button class="admin-button admin-button-secondary" :disabled="cargando || pagina <= 1" @click="pagina--; cargar()">Anterior</button>
          <button class="admin-button admin-button-secondary" :disabled="cargando || pagina * 20 >= cantidad" @click="pagina++; cargar()">Siguiente</button>
        </div>
      </div>
    </div>
  </section>
</template>
