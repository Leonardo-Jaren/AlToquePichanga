<script setup>
import { onMounted, ref } from 'vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { plataformaApi } from '@/modules/empresas/services/empresas'

const empresas = ref([])
const cantidad = ref(0)
const pagina = ref(1)
const consulta = ref('')
const estado = ref('')
const cargando = ref(false)
const cambiando = ref(null)
const error = ref('')
const filtrosEstado = [
  ['', 'Todos'], ['pendiente', 'Pendientes'], ['activa', 'Activas'],
  ['rechazada', 'Rechazadas'], ['suspendida', 'Suspendidas'],
]
const estados = {
  pendiente: ['activa', 'rechazada'],
  activa: ['suspendida'],
  rechazada: ['activa'],
  suspendida: ['activa'],
}
const accion = (valor) => ({
  activa: 'Aprobar / activar',
  rechazada: 'Rechazar',
  suspendida: 'Suspender',
}[valor] || 'Reactivar')

onMounted(cargar)

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await plataformaApi.empresas({ page: pagina.value, q: consulta.value, estado: estado.value })
    empresas.value = data.results
    cantidad.value = data.count
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cargar el listado de empresas.'
  } finally {
    cargando.value = false
  }
}
async function filtrar() { pagina.value = 1; await cargar() }
async function cambiar(item, nuevoEstado) {
  const texto = '¿Quieres ' + accion(nuevoEstado).toLowerCase() + ' '
    + (item.nombre_comercial || item.razon_social || item.nombre) + '?'
  if (!window.confirm(texto)) return
  cambiando.value = item.id
  error.value = ''
  try {
    const { data } = await plataformaApi.estadoEmpresa(item.id, nuevoEstado)
    empresas.value = empresas.value.map((empresa) => empresa.id === item.id ? data : empresa)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cambiar el estado de la empresa.'
  } finally {
    cambiando.value = null
  }
}
async function cambiarSuscripcion(item, nuevoEstado) {
  const texto = nuevoEstado === 'cancelada'
    ? '¿Cancelar la suscripción de ' + item.nombre + '?'
    : '¿Suspender la suscripción de ' + item.nombre + '?'
  if (!window.confirm(texto)) return
  cambiando.value = item.id
  error.value = ''
  try {
    await plataformaApi.estadoSuscripcion(item.id, nuevoEstado)
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cambiar la suscripción.'
  } finally {
    cambiando.value = null
  }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="empresas-plataforma">
    <div>
      <h2 id="empresas-plataforma" class="text-xl font-bold">Empresas</h2>
      <p class="mt-1 text-sm text-app-text-muted">La consulta administrativa queda registrada.</p>
    </div>
    <form class="admin-card grid gap-3 sm:grid-cols-[minmax(0,1fr)_200px_auto]" @submit.prevent="filtrar">
      <label><span class="admin-label">Buscar</span><input v-model.trim="consulta" class="admin-field" placeholder="Nombre, razón social o RUC"></label>
      <label><span class="admin-label">Estado</span><select v-model="estado" class="admin-field"><option v-for="opcion in filtrosEstado" :key="opcion[0]" :value="opcion[0]">{{ opcion[1] }}</option></select></label>
      <button class="admin-button admin-button-secondary self-end">Buscar</button>
    </form>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="cargando" role="status" class="text-sm text-app-text-muted">Cargando empresas…</p>
    <div v-else-if="!empresas.length" class="admin-card">
      <p class="font-semibold">No hay empresas que coincidan con estos filtros.</p>
      <p class="mt-1 text-sm text-app-text-muted">Prueba otro estado o término de búsqueda.</p>
    </div>
    <section v-else class="admin-card" :aria-label="cantidad + ' empresas'">
      <p class="mb-2 text-sm text-app-text-muted">{{ cantidad }} empresas · página {{ pagina }}</p>
      <article v-for="item in empresas" :key="item.id" class="admin-row-card lg:grid-cols-[minmax(0,1.5fr)_minmax(130px,.7fr)_minmax(180px,1fr)_auto] lg:items-center">
        <div class="min-w-0">
          <p class="break-words font-bold">{{ item.nombre_comercial || item.razon_social || item.nombre }}</p>
          <p class="break-words text-sm text-app-text-muted">{{ item.razon_social || 'Razón social pendiente' }}<span v-if="item.ruc"> · RUC {{ item.ruc }}</span></p>
          <p class="mt-1 text-sm">{{ item.responsables.length }} responsables · {{ item.cantidad_sedes }} sedes activas</p>
        </div>
        <div class="flex items-center gap-2"><span class="text-sm text-app-text-muted">Empresa</span><EstadoEtiqueta :estado="item.estado" /></div>
        <div>
          <p class="text-sm font-semibold">{{ item.suscripcion?.plan || 'Sin suscripción' }}</p>
          <p class="text-sm text-app-text-muted">{{ item.suscripcion?.vencimiento ? 'Vence ' + item.suscripcion.vencimiento : 'Sin periodo vigente' }}</p>
          <EstadoEtiqueta v-if="item.suscripcion" :estado="item.suscripcion.estado" />
        </div>
        <div class="flex flex-wrap gap-2">
          <button v-for="destino in estados[item.estado]" :key="destino"
            :class="['admin-button', destino === 'rechazada' || destino === 'suspendida' ? 'admin-button-danger' : 'admin-button-primary']"
            :disabled="cambiando === item.id" @click="cambiar(item, destino)">{{ cambiando === item.id ? 'Guardando…' : accion(destino) }}</button>
          <button v-if="item.suscripcion && item.suscripcion.estado !== 'cancelada'"
            class="admin-button admin-button-quiet" :disabled="cambiando === item.id"
            @click="cambiarSuscripcion(item, item.suscripcion.estado === 'suspendida' ? 'cancelada' : 'suspendida')">
            {{ item.suscripcion.estado === 'suspendida' ? 'Cancelar plan' : 'Suspender plan' }}
          </button>
        </div>
        <details class="text-sm lg:col-span-4">
          <summary class="min-h-11 cursor-pointer py-3 font-semibold text-app-link">Ver responsables y datos de gestión</summary>
          <div class="grid gap-4 border-t border-app-border pt-4 sm:grid-cols-2">
            <div><p class="font-semibold">Responsables</p><ul class="mt-1 space-y-1 text-app-text-muted"><li v-for="persona in item.responsables" :key="persona.id">{{ persona.nombre || persona.correo }} · {{ persona.correo }}</li></ul></div>
            <div><p class="font-semibold">Contacto empresarial</p><p class="mt-1 break-words text-app-text-muted">{{ item.correo_contacto || 'Sin correo de contacto' }} · {{ item.telefono_contacto || 'Sin teléfono' }}</p><p class="mt-1 text-app-text-muted">{{ item.direccion_administrativa || 'Sin dirección administrativa' }}</p></div>
          </div>
        </details>
      </article>
      <div class="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-app-border pt-4">
        <span class="text-sm text-app-text-muted">Mostrando {{ empresas.length }} de {{ cantidad }}</span>
        <div class="flex gap-2">
          <button class="admin-button admin-button-secondary" :disabled="cargando || pagina <= 1" @click="pagina--; cargar()">Anterior</button>
          <button class="admin-button admin-button-secondary" :disabled="cargando || pagina * 20 >= cantidad" @click="pagina++; cargar()">Siguiente</button>
        </div>
      </div>
    </section>
  </section>
</template>
