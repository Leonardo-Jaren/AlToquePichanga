<script setup>
import { onMounted, ref } from 'vue'
import AdminLayout from '@/modules/administracion/components/AdminLayout.vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import api from '@/shared/services/api'
import GestionCanchasPanel from '@/modules/canchas/components/GestionCanchasPanel.vue'
import GestionHorariosPanel from '@/modules/horarios/components/GestionHorariosPanel.vue'

const sedes = ref([])
const cargando = ref(false)
const error = ref('')
const vista = ref('sedes')

onMounted(async () => {
  cargando.value = true
  try { sedes.value = (await api.get('/sedes/')).data }
  catch (fallo) { error.value = fallo.response?.data?.detail || 'No se pudieron cargar tus sedes.' }
  finally { cargando.value = false }
})
</script>

<template>
  <AdminLayout titulo="Vista de cajero" descripcion="Tus accesos quedan limitados a las sedes que la empresa te asignó.">
    <p v-if="error" role="alert" class="admin-error mb-4">{{ error }}</p>
    <p v-if="cargando" role="status" class="admin-card">Cargando tus sedes…</p>
    <div v-else-if="!sedes.length" class="admin-card">
      <h2 class="font-bold">No tienes sedes asignadas.</h2>
      <p class="mt-2 text-sm text-app-text-muted">Pide al dueño de la empresa que revise tu acceso.</p>
    </div>
    <section v-else class="space-y-4" aria-labelledby="sedes-cajero">
      <nav class="flex flex-wrap gap-2" aria-label="Consulta de sede">
        <button class="admin-button" :class="vista === 'sedes' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="vista === 'sedes'" @click="vista = 'sedes'">Sedes autorizadas</button>
        <button class="admin-button" :class="vista === 'canchas' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="vista === 'canchas'" @click="vista = 'canchas'">Consultar canchas</button>
        <button class="admin-button" :class="vista === 'horarios' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="vista === 'horarios'" @click="vista = 'horarios'">Consultar horarios</button>
      </nav>
      <GestionCanchasPanel v-if="vista === 'canchas'" :key="'consulta-canchas-cajero'" :sedes="sedes" :solo-lectura="true" />
      <GestionHorariosPanel v-else-if="vista === 'horarios'" :key="'consulta-horarios-cajero'" :sedes="sedes" :solo-lectura="true" />
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
