<script setup>
import { computed, ref, watch } from 'vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { empresasApi } from '../services/empresas'

const props = defineProps({
  empresa: { type: Object, required: true },
  sedes: { type: Array, default: () => [] },
  suscripcion: { type: Object, default: null },
})
const personal = ref([])
const invitaciones = ref([])
const cargando = ref(false)
const guardando = ref(false)
const rol = ref('cajero')
const correo = ref('')
const sedesElegidas = ref([])
const error = ref('')
const mensaje = ref('')
const puedeInvitar = computed(() => props.empresa.activa && props.suscripcion?.estado === 'activa')

watch(() => props.empresa.id, cargar, { immediate: true })

async function cargar() {
  if (!props.empresa?.id) return
  cargando.value = true
  error.value = ''
  try {
    const { data } = await empresasApi.listarPersonal(props.empresa.id)
    personal.value = data.personal
    invitaciones.value = data.invitaciones
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cargar el equipo de esta empresa.'
  } finally {
    cargando.value = false
  }
}

async function guardar() {
  guardando.value = true
  error.value = ''
  mensaje.value = ''
  try {
    const { data } = await empresasApi.invitarPersonal(props.empresa.id, {
      correo: correo.value,
      rol: rol.value,
      sedes: rol.value === 'dueno' ? [] : sedesElegidas.value,
    })
    mensaje.value = data.tipo === 'invitacion'
      ? 'Invitación registrada. El correo saldrá cuando la cola de correo la procese.'
      : (data.nombre || data.correo) + ' ya forma parte del equipo.'
    correo.value = ''
    sedesElegidas.value = []
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo asignar el acceso.'
  } finally {
    guardando.value = false
  }
}

async function revocar(membresia) {
  if (!window.confirm('¿Revocar el acceso de ' + (membresia.nombre || membresia.correo) + '?')) return
  try {
    await empresasApi.revocarPersonal(props.empresa.id, membresia.id)
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo revocar el acceso.'
  }
}
async function cancelar(invitacion) {
  if (!window.confirm('¿Cancelar la invitación enviada a ' + invitacion.correo + '?')) return
  try {
    await empresasApi.revocarInvitacion(props.empresa.id, invitacion.id)
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cancelar la invitación.'
  }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="equipo-titulo">
    <div>
      <h2 id="equipo-titulo" class="text-xl font-bold">Equipo y accesos</h2>
      <p class="mt-1 text-sm text-app-text-muted">Asigna roles de empresa y las sedes que pueden administrar.</p>
    </div>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>

    <form class="admin-card grid gap-4 md:grid-cols-2" novalidate :aria-busy="guardando" @submit.prevent="guardar">
      <div class="md:col-span-2">
        <h3 class="text-lg font-bold">Agregar una persona</h3>
        <p class="mt-1 text-sm text-app-text-muted">Las cuentas existentes reciben acceso. Si el correo aún no tiene cuenta, queda una invitación de un solo uso.</p>
      </div>
      <label>
        <span class="admin-label">Correo electrónico</span>
        <input v-model.trim="correo" class="admin-field" type="email" autocomplete="email" maxlength="254" required>
      </label>
      <label>
        <span class="admin-label">Rol en esta empresa</span>
        <select v-model="rol" class="admin-field">
          <option value="administrador_sede">Administrador de sede</option>
          <option value="cajero">Cajero / Empleado</option>
          <option value="dueno">Dueño de empresa</option>
        </select>
      </label>
      <fieldset v-if="rol !== 'dueno'" class="md:col-span-2">
        <legend class="admin-label">Sedes asignadas</legend>
        <p class="mb-3 text-sm text-app-text-muted">El rol puede acceder solo a las sedes marcadas.</p>
        <div v-if="!sedes.filter((sede) => sede.activa).length" class="text-sm text-app-text-muted">No hay sedes activas para asignar.</div>
        <label v-for="sede in sedes.filter((item) => item.activa)" :key="sede.id" class="mb-2 flex min-h-11 items-center gap-3 rounded-lg border border-app-border px-3">
          <input v-model="sedesElegidas" type="checkbox" :value="sede.id" class="size-4 accent-[var(--brand-lime)]">
          <span>{{ sede.nombre }}<span class="ml-2 text-sm text-app-text-muted">{{ sede.distrito }}</span></span>
        </label>
      </fieldset>
      <p v-if="!puedeInvitar && rol !== 'dueno'" class="admin-error md:col-span-2">La empresa necesita aprobación y una suscripción vigente para agregar personal operativo.</p>
      <button class="admin-button admin-button-primary md:col-span-2 md:justify-self-start"
        :disabled="guardando || !correo || (rol !== 'dueno' && (!puedeInvitar || !sedesElegidas.length))">
        {{ guardando ? 'Guardando…' : 'Asignar o invitar' }}
      </button>
    </form>

    <section class="admin-card" aria-labelledby="personal-actual">
      <h3 id="personal-actual" class="text-lg font-bold">Personas de la empresa</h3>
      <p v-if="cargando" role="status" class="mt-4 text-sm text-app-text-muted">Cargando el equipo…</p>
      <p v-else-if="!personal.length" class="mt-4 text-sm text-app-text-muted">Aún no hay personas asignadas.</p>
      <div v-else class="mt-2">
        <article v-for="miembro in personal" :key="miembro.id" class="admin-row-card sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
          <div class="min-w-0">
            <p class="break-words font-semibold">{{ miembro.nombre || miembro.correo }}</p>
            <p class="break-words text-sm text-app-text-muted">{{ miembro.correo }}</p>
            <p class="mt-1 text-sm">{{ miembro.rol === 'dueno' ? 'Dueño de empresa' : miembro.rol === 'cajero' ? 'Cajero / Empleado' : 'Administrador de sede' }}
              <span v-if="miembro.sedes.length"> · {{ miembro.sedes.map((id) => sedes.find((s) => s.id === id)?.nombre).filter(Boolean).join(', ') }}</span>
            </p>
          </div>
          <EstadoEtiqueta :estado="miembro.activa ? 'activa' : 'suspendida'" />
          <button class="admin-button admin-button-danger" :disabled="!miembro.activa" @click="revocar(miembro)">Revocar</button>
        </article>
      </div>
    </section>

    <section v-if="invitaciones.length" class="admin-card" aria-labelledby="invitaciones-pendientes">
      <h3 id="invitaciones-pendientes" class="text-lg font-bold">Invitaciones</h3>
      <article v-for="invitacion in invitaciones" :key="invitacion.id" class="admin-row-card sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
        <div class="min-w-0">
          <p class="break-words font-semibold">{{ invitacion.correo }}</p>
          <p class="text-sm text-app-text-muted">{{ invitacion.rol }} · vence {{ new Date(invitacion.vence_en).toLocaleDateString('es-PE') }}</p>
        </div>
        <EstadoEtiqueta :estado="invitacion.estado" />
        <button class="admin-button admin-button-danger" :disabled="invitacion.estado !== 'pendiente'" @click="cancelar(invitacion)">Cancelar invitación</button>
      </article>
    </section>
  </section>
</template>
