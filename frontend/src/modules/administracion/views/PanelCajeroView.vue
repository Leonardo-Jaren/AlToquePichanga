<script setup>
import { computed, onMounted, ref } from 'vue'
import AdminLayout from '@/modules/administracion/components/AdminLayout.vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import api from '@/shared/services/api'
import GestionCanchasPanel from '@/modules/canchas/components/GestionCanchasPanel.vue'
import GestionHorariosPanel from '@/modules/horarios/components/GestionHorariosPanel.vue'
import GestionTarifasPanel from '@/modules/tarifas/components/paneles/GestionTarifasPanel.vue'
import CalendarioAdminPanel from '@/modules/calendario/components/paneles/CalendarioAdminPanel.vue'
import ReservasAdminPanel from '@/modules/reservas/components/ReservasAdminPanel.vue'
import PagosAdminPanel from '@/modules/pagos/components/PagosAdminPanel.vue'

const sedes = ref([])
const cargando = ref(false)
const error = ref('')
const vista = ref('sedes')
const menu = [
  { id: 'sedes', nombre: 'Sedes autorizadas' },
  { id: 'canchas', nombre: 'Consultar canchas' },
  { id: 'horarios', nombre: 'Consultar horarios' },
  { id: 'tarifas', nombre: 'Consultar tarifas' },
  { id: 'calendario', nombre: 'Calendario' },
  { id: 'reservas', nombre: 'Reservas' },
  { id: 'pagos', nombre: 'Pagos' },
]
const titulos = {
  sedes: ['Sedes autorizadas', 'Tus accesos quedan limitados a las sedes que la empresa te asignó.'],
  canchas: ['Consultar canchas', 'Consulta las canchas de tus sedes autorizadas.'],
  horarios: ['Consultar horarios', 'Revisa horarios y cierres sin modificar su configuración.'],
  tarifas: ['Consultar tarifas', 'Consulta precios por cancha y horario en tus sedes autorizadas.'],
  calendario: ['Calendario operativo', 'Consulta horarios operativos, cierres y precios de tus sedes.'],
  reservas: ['Reservas de tus sedes', 'Consulta las solicitudes dentro de tus sedes autorizadas.'],
  pagos: ['Pagos de tus sedes', 'Revisa comprobantes solo en las sedes que tienes asignadas.'],
}
const titulo = computed(() => titulos[vista.value][0])
const descripcion = computed(() => titulos[vista.value][1])

onMounted(async () => {
  cargando.value = true
  try { sedes.value = (await api.get('/sedes/')).data }
  catch (fallo) { error.value = fallo.response?.data?.detail || 'No se pudieron cargar tus sedes.' }
  finally { cargando.value = false }
})
</script>

<template>
  <AdminLayout :titulo="titulo" :descripcion="descripcion" :secciones="menu" :activa="vista" @cambiar-seccion="vista = $event">
    <p v-if="error" role="alert" class="admin-error mb-4">{{ error }}</p>
    <p v-if="cargando" role="status" class="admin-card">Cargando tus sedes…</p>
    <div v-else-if="!sedes.length" class="admin-card">
      <h2 class="font-bold">No tienes sedes asignadas.</h2>
      <p class="mt-2 text-sm text-app-text-muted">Pide al dueño de la empresa que revise tu acceso.</p>
    </div>
    <section v-else class="space-y-4" aria-labelledby="sedes-cajero">
      <GestionCanchasPanel v-if="vista === 'canchas'" :key="'consulta-canchas-cajero'" :sedes="sedes" :solo-lectura="true" />
      <GestionHorariosPanel v-else-if="vista === 'horarios'" :key="'consulta-horarios-cajero'" :sedes="sedes" :solo-lectura="true" />
      <GestionTarifasPanel v-else-if="vista === 'tarifas'" :key="'consulta-tarifas-cajero'" :sedes="sedes" :solo-lectura="true" />
      <CalendarioAdminPanel v-else-if="vista === 'calendario'" :key="'consulta-calendario-cajero'" :sedes="sedes" />
      <ReservasAdminPanel v-else-if="vista === 'reservas'" :key="'consulta-reservas-cajero'" />
      <PagosAdminPanel v-else-if="vista === 'pagos'" :key="'consulta-pagos-cajero'" :sedes="sedes" />
      <template v-else>
      <h2 id="sedes-cajero" class="text-lg font-bold">Sedes autorizadas</h2>
      <article v-for="sede in sedes" :key="sede.id" class="admin-card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div><p class="text-sm text-app-text-muted">{{ sede.empresa }}</p><h3 class="mt-1 text-lg font-bold">{{ sede.nombre }}</h3><p class="mt-1 text-sm text-app-text-muted">{{ sede.direccion }}</p></div>
          <EstadoEtiqueta :estado="sede.activa ? 'activa' : 'suspendida'" />
        </div>
        <p class="mt-3 break-words text-sm">{{ sede.telefono_contacto || sede.correo_contacto || 'Sin contacto registrado' }}</p>
      </article>
      <p class="rounded-xl bg-app-surface-2 p-4 text-sm text-app-text-muted">Las funciones de caja presencial se implementarán en una fase posterior.</p>
      </template>
    </section>
  </AdminLayout>
</template>
