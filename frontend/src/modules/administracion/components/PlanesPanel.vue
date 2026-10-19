<script setup>
import { onMounted, reactive, ref } from 'vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { plataformaApi } from '@/modules/empresas/services/empresas'
import { formatearDinero } from '@/shared/services/dinero'

const planes = ref([])
const abierto = ref(false)
const editando = ref(null)
const cargando = ref(false)
const guardando = ref(false)
const error = ref('')
const mensaje = ref('')
const vacio = () => ({
  nombre: '', descripcion: '', precio: '', moneda: 'PEN', frecuencia: 'mensual',
  maximo_sedes: '', maximo_empleados: '', maximo_canchas: '', activo: true,
})
const form = reactive(vacio())

onMounted(cargar)
async function cargar() {
  cargando.value = true
  error.value = ''
  try { planes.value = (await plataformaApi.planes()).data }
  catch (fallo) { error.value = fallo.response?.data?.detail || 'No se pudieron cargar los planes.' }
  finally { cargando.value = false }
}
function nuevo() { Object.assign(form, vacio()); editando.value = null; abierto.value = true }
function editar(plan) {
  Object.assign(form, { ...plan, precio: String(plan.precio),
    maximo_sedes: plan.maximo_sedes ?? '', maximo_empleados: plan.maximo_empleados ?? '',
    maximo_canchas: plan.maximo_canchas ?? '' })
  editando.value = plan.id
  abierto.value = true
  mensaje.value = ''
}
function valorLimite(valor) { return valor === '' ? null : Number(valor) }
async function guardar() {
  guardando.value = true
  error.value = ''
  mensaje.value = ''
  const datos = {
    ...form,
    nombre: form.nombre.trim(),
    moneda: form.moneda.trim().toUpperCase(),
    precio: String(form.precio).trim().replace(',', '.'),
    maximo_sedes: valorLimite(form.maximo_sedes),
    maximo_empleados: valorLimite(form.maximo_empleados),
    maximo_canchas: valorLimite(form.maximo_canchas),
  }
  try {
    await plataformaApi.guardarPlan(datos, editando.value)
    abierto.value = false
    mensaje.value = editando.value ? 'Plan actualizado.' : 'Plan creado.'
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo guardar el plan.'
  } finally { guardando.value = false }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="planes-titulo">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 id="planes-titulo" class="text-xl font-bold">Planes SaaS</h2>
        <p class="mt-1 max-w-3xl text-sm text-app-text-muted">Los cambios al precio actualizan planes futuros. Los periodos ya contratados guardan su propio precio.</p>
      </div>
      <button class="admin-button admin-button-primary" @click="nuevo">Crear plan</button>
    </div>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>
    <p v-if="cargando" role="status" class="text-sm text-app-text-muted">Cargando planes…</p>
    <div v-else-if="!planes.length" class="admin-card">
      <p class="font-semibold">Todavía no hay planes configurados.</p>
      <p class="mt-1 text-sm text-app-text-muted">Define precio, periodicidad y límites antes de ofrecerlos a las empresas.</p>
    </div>
    <div v-else class="grid gap-4 lg:grid-cols-2">
      <article v-for="plan in planes" :key="plan.id" class="admin-card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div><h3 class="text-lg font-bold">{{ plan.nombre }}</h3><p class="mt-1 text-sm text-app-text-muted">{{ plan.descripcion || 'Sin descripción' }}</p></div>
          <EstadoEtiqueta :estado="plan.activo ? 'activa' : 'suspendida'" />
        </div>
        <p class="mt-5 text-2xl font-bold tabular-nums">{{ formatearDinero(plan.precio, plan.moneda) }}</p>
        <p class="text-sm text-app-text-muted">{{ plan.frecuencia }}</p>
        <dl class="mt-4 grid grid-cols-2 gap-3 border-t border-app-border pt-4 text-sm">
          <div><dt class="text-app-text-muted">Sedes</dt><dd class="font-semibold">{{ plan.maximo_sedes ?? 'Sin límite configurado' }}</dd></div>
          <div><dt class="text-app-text-muted">Empleados</dt><dd class="font-semibold">{{ plan.maximo_empleados ?? 'Sin límite configurado' }}</dd></div>
          <div><dt class="text-app-text-muted">Canchas (futuro)</dt><dd class="font-semibold">{{ plan.maximo_canchas ?? 'Sin límite configurado' }}</dd></div>
        </dl>
        <button class="admin-button admin-button-secondary mt-5" @click="editar(plan)">Editar plan</button>
      </article>
    </div>

    <form v-if="abierto" class="admin-card grid gap-4 md:grid-cols-2" novalidate :aria-busy="guardando" @submit.prevent="guardar">
      <div class="md:col-span-2"><h3 class="text-lg font-bold">{{ editando ? 'Editar plan' : 'Nuevo plan' }}</h3></div>
      <label><span class="admin-label">Nombre *</span><input v-model.trim="form.nombre" class="admin-field" maxlength="100" required></label>
      <label><span class="admin-label">Precio *</span><input v-model.trim="form.precio" class="admin-field" type="text" inputmode="decimal" pattern="[0-9]+([.,][0-9]{1,2})?" autocomplete="off" required></label>
      <label><span class="admin-label">Moneda <span class="font-normal text-app-text-muted">(código de 3 letras)</span></span><input v-model.trim="form.moneda" class="admin-field" maxlength="3" pattern="[A-Za-z]{3}" required></label>
      <label><span class="admin-label">Periodicidad</span><select v-model="form.frecuencia" class="admin-field"><option value="mensual">Mensual</option><option value="trimestral">Trimestral</option><option value="semestral">Semestral</option><option value="anual">Anual</option></select></label>
      <label><span class="admin-label">Máximo de sedes activas</span><input v-model="form.maximo_sedes" class="admin-field" type="number" min="0" step="1"></label>
      <label><span class="admin-label">Máximo de empleados</span><input v-model="form.maximo_empleados" class="admin-field" type="number" min="0" step="1"></label>
      <label><span class="admin-label">Máximo de canchas (configuración futura)</span><input v-model="form.maximo_canchas" class="admin-field" type="number" min="0" step="1"></label>
      <label class="flex min-h-11 items-center gap-3"><input v-model="form.activo" type="checkbox" class="size-4 accent-[var(--brand-lime)]"><span class="font-semibold">Ofrecer este plan</span></label>
      <label class="md:col-span-2"><span class="admin-label">Descripción</span><textarea v-model.trim="form.descripcion" class="admin-field min-h-20" maxlength="4000" rows="3" /></label>
      <p class="text-sm text-app-text-muted md:col-span-2">Un límite vacío se guarda sin máximo. La plataforma configura los valores comerciales.</p>
      <p v-if="error" role="alert" class="admin-error md:col-span-2">{{ error }}</p>
      <div class="flex flex-wrap gap-2 md:col-span-2">
        <button class="admin-button admin-button-primary" :disabled="guardando">{{ guardando ? 'Guardando…' : 'Guardar plan' }}</button>
        <button class="admin-button admin-button-secondary" type="button" :disabled="guardando" @click="abierto = false">Cancelar</button>
      </div>
    </form>
  </section>
</template>
