<script setup>
import { computed, ref, watch } from 'vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { empresasApi } from '../services/empresas'
import { formatearDinero } from '@/shared/services/dinero'

const props = defineProps({ empresa: { type: Object, required: true } })
const resumen = ref(null)
const planes = ref([])
const planId = ref('')
const medio = ref('')
const referencia = ref('')
const nota = ref('')
const cargando = ref(false)
const guardando = ref(false)
const error = ref('')
const mensaje = ref('')
const solicitudPendiente = computed(() => resumen.value?.solicitudes?.some((item) => item.estado === 'pendiente'))
const limite = (valor) => valor == null ? 'Sin límite configurado' : String(valor)

watch(() => props.empresa.id, cargar, { immediate: true })

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const [estado, opciones] = await Promise.all([
      empresasApi.suscripcion(props.empresa.id),
      empresasApi.planes(),
    ])
    resumen.value = estado.data
    planes.value = opciones.data
    if (!planId.value && planes.value.length) planId.value = String(planes.value[0].id)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cargar la suscripción.'
  } finally {
    cargando.value = false
  }
}

function fecha(valor) {
  return valor ? new Date(valor + 'T12:00:00').toLocaleDateString('es-PE', {
    day: 'numeric', month: 'long', year: 'numeric',
  }) : 'Pendiente'
}

async function solicitar() {
  guardando.value = true
  error.value = ''
  mensaje.value = ''
  try {
    await empresasApi.solicitarSuscripcion(props.empresa.id, {
      plan_id: Number(planId.value), medio_declarado: medio.value,
      referencia_declarada: referencia.value, nota: nota.value,
    })
    mensaje.value = 'Solicitud recibida. La empresa no se activa hasta que la plataforma la revise.'
    medio.value = ''
    referencia.value = ''
    nota.value = ''
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo enviar la solicitud.'
  } finally {
    guardando.value = false
  }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="suscripcion-titulo">
    <div>
      <h2 id="suscripcion-titulo" class="text-xl font-bold">Suscripción de AlToque Pichanga</h2>
      <p class="mt-1 text-sm text-app-text-muted">La suscripción cubre el uso de la plataforma para tu empresa.</p>
    </div>
    <p v-if="cargando" role="status" class="text-sm text-app-text-muted">Consultando planes…</p>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>

    <article v-if="resumen?.suscripcion" class="admin-card">
      <div class="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p class="text-sm text-app-text-muted">Plan contratado</p>
          <h3 class="mt-1 text-xl font-bold">{{ resumen.suscripcion.plan.nombre }}</h3>
          <p class="mt-1">{{ formatearDinero(resumen.suscripcion.importe_acordado, resumen.suscripcion.moneda_acordada) }}
            <span class="text-sm text-app-text-muted"> / {{ resumen.suscripcion.frecuencia_acordada }}</span>
          </p>
        </div>
        <EstadoEtiqueta :estado="resumen.suscripcion.estado" />
      </div>
      <dl class="mt-5 grid gap-4 sm:grid-cols-2">
        <div><dt class="text-sm text-app-text-muted">Inicio del periodo</dt><dd class="font-semibold">{{ fecha(resumen.suscripcion.fecha_inicio) }}</dd></div>
        <div><dt class="text-sm text-app-text-muted">Vencimiento</dt><dd class="font-semibold">{{ fecha(resumen.suscripcion.fecha_vencimiento) }}</dd></div>
        <div><dt class="text-sm text-app-text-muted">Límite de sedes activas</dt><dd class="font-semibold">{{ limite(resumen.suscripcion.plan.maximo_sedes) }}</dd></div>
        <div><dt class="text-sm text-app-text-muted">Límite de empleados</dt><dd class="font-semibold">{{ limite(resumen.suscripcion.plan.maximo_empleados) }}</dd></div>
      </dl>
      <div v-if="resumen.suscripcion.periodos.length" class="mt-6 border-t border-app-border pt-4">
        <h4 class="font-semibold">Periodos registrados</h4>
        <ul class="mt-2 space-y-2 text-sm">
          <li v-for="periodo in resumen.suscripcion.periodos" :key="periodo.fecha_inicio + periodo.plan" class="flex flex-wrap justify-between gap-2">
            <span>{{ periodo.plan }} · {{ fecha(periodo.fecha_inicio) }} al {{ fecha(periodo.fecha_vencimiento) }}</span>
            <span class="tabular-nums">{{ formatearDinero(periodo.importe, periodo.moneda) }}</span>
          </li>
        </ul>
      </div>
    </article>
    <div v-else class="admin-card">
      <p class="font-semibold">Aún no hay una suscripción activa.</p>
      <p class="mt-1 text-sm text-app-text-muted">Puedes enviar una solicitud a la plataforma para iniciar el servicio.</p>
    </div>

    <section v-if="planes.length" class="space-y-4" aria-labelledby="planes-disponibles">
      <div>
        <h3 id="planes-disponibles" class="text-lg font-bold">Planes disponibles</h3>
        <p class="text-sm text-app-text-muted">El importe queda guardado en la solicitud. La plataforma revisa el pago manualmente.</p>
      </div>
      <div class="grid gap-4 lg:grid-cols-2">
        <label v-for="plan in planes" :key="plan.id"
          :class="['admin-card block cursor-pointer', planId === String(plan.id) ? 'border-brand-lime ring-2 ring-brand-lime' : '']">
          <span class="flex items-start justify-between gap-3">
            <span><span class="block text-lg font-bold">{{ plan.nombre }}</span><span class="mt-1 block text-sm text-app-text-muted">{{ plan.descripcion }}</span></span>
            <input v-model="planId" type="radio" name="plan" :value="String(plan.id)" class="mt-1 size-4 accent-[var(--brand-lime)]" :aria-label="'Seleccionar ' + plan.nombre">
          </span>
          <span class="mt-4 block text-2xl font-bold">{{ formatearDinero(plan.precio, plan.moneda) }}</span>
          <span class="text-sm text-app-text-muted">{{ plan.frecuencia }}</span>
          <span class="mt-4 grid grid-cols-2 gap-2 border-t border-app-border pt-3 text-sm">
            <span>Sedes: {{ limite(plan.maximo_sedes) }}</span><span>Empleados: {{ limite(plan.maximo_empleados) }}</span>
          </span>
        </label>
      </div>
      <form v-if="!solicitudPendiente" class="admin-card grid gap-4 md:grid-cols-2" @submit.prevent="solicitar" :aria-busy="guardando">
        <label><span class="admin-label">Medio declarado <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="medio" class="admin-field" maxlength="40"></label>
        <label><span class="admin-label">Referencia de pago <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="referencia" class="admin-field" maxlength="120"></label>
        <label class="md:col-span-2"><span class="admin-label">Nota para la plataforma <span class="font-normal text-app-text-muted">(opcional)</span></span><textarea v-model.trim="nota" class="admin-field min-h-20" maxlength="500" rows="3" /></label>
        <button class="admin-button admin-button-primary md:justify-self-start" :disabled="guardando || !planId">{{ guardando ? 'Enviando…' : 'Solicitar activación o renovación' }}</button>
      </form>
      <p v-else class="admin-error">Hay una solicitud pendiente. La plataforma debe resolverla antes de enviar otra.</p>
    </section>
    <p v-else-if="!cargando" class="admin-card text-sm text-app-text-muted">La plataforma todavía no publicó planes disponibles.</p>

    <section v-if="resumen?.solicitudes?.length" class="admin-card" aria-labelledby="historial-solicitudes">
      <h3 id="historial-solicitudes" class="text-lg font-bold">Solicitudes recientes</h3>
      <article v-for="solicitud in resumen.solicitudes" :key="solicitud.id" class="admin-row-card sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center">
        <div><p class="font-semibold">{{ solicitud.plan }} · {{ solicitud.tipo }}</p><p class="text-sm text-app-text-muted">{{ formatearDinero(solicitud.precio, solicitud.moneda) }} · {{ fecha(solicitud.creada_en.slice(0, 10)) }}</p></div>
        <EstadoEtiqueta :estado="solicitud.estado" />
      </article>
    </section>
  </section>
</template>
