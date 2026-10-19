<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AdminLayout from '@/modules/administracion/components/AdminLayout.vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { empresasApi } from '@/modules/empresas/services/empresas'
import api from '@/shared/services/api'
import GestionCanchasPanel from '@/modules/canchas/components/GestionCanchasPanel.vue'
import GestionHorariosPanel from '@/modules/horarios/components/GestionHorariosPanel.vue'

const sedes = ref([])
const seleccionada = ref(null)
const cargando = ref(false)
const guardando = ref(false)
const editando = ref(false)
const error = ref('')
const mensaje = ref('')
const form = reactive({})
const portada = ref(null)
const imagenGaleria = ref(null)
const vista = ref('sede')
const titulo = computed(() => editando.value ? 'Editar sede asignada' : 'Tus sedes asignadas')

onMounted(cargar)
async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await api.get('/sedes/')
    sedes.value = data
    if (seleccionada.value) seleccionada.value = data.find((sede) => sede.id === seleccionada.value.id) || null
    if (!seleccionada.value && data.length) seleccionada.value = data[0]
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudieron cargar las sedes asignadas.'
  } finally { cargando.value = false }
}
function seleccionarSede(sede) {
  seleccionada.value = sede
  editando.value = false
  vista.value = 'sede'
}
function editar() {
  Object.assign(form, {
    nombre: seleccionada.value.nombre, direccion: seleccionada.value.direccion,
    departamento: seleccionada.value.departamento, provincia: seleccionada.value.provincia,
    distrito: seleccionada.value.distrito, telefono_contacto: seleccionada.value.telefono_contacto,
    whatsapp_contacto: seleccionada.value.whatsapp_contacto,
    correo_contacto: seleccionada.value.correo_contacto,
    descripcion: seleccionada.value.descripcion,
    latitud: seleccionada.value.latitud || '',
    longitud: seleccionada.value.longitud || '',
  })
  portada.value = null
  editando.value = true
}
function elegirPortada(evento) { portada.value = evento.target.files?.[0] || null }
function elegirImagenGaleria(evento) { imagenGaleria.value = evento.target.files?.[0] || null }
async function guardar() {
  guardando.value = true
  error.value = ''
  try {
    const datos = {
      ...form,
      latitud: form.latitud === '' ? null : form.latitud,
      longitud: form.longitud === '' ? null : form.longitud,
    }
    let actualizada = (await empresasApi.actualizarSede(seleccionada.value.id, datos)).data
    if (portada.value) {
      const archivo = new FormData()
      archivo.append('imagen_principal', portada.value)
      actualizada = (await empresasApi.actualizarSede(seleccionada.value.id, archivo)).data
    }
    seleccionada.value = actualizada
    sedes.value = sedes.value.map((item) => item.id === actualizada.id ? actualizada : item)
    editando.value = false
    portada.value = null
    mensaje.value = 'Datos de la sede guardados.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudieron guardar los datos.'
  } finally { guardando.value = false }
}
async function subirImagenGaleria() {
  if (!imagenGaleria.value) return
  try {
    await empresasApi.imagenSede(seleccionada.value.id, imagenGaleria.value)
    imagenGaleria.value = null
    await cargar()
    mensaje.value = 'Imagen añadida a la sede.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo subir la imagen.'
  }
}
async function retirarImagen(imagen) {
  if (!window.confirm('¿Quieres retirar esta imagen de la sede?')) return
  try {
    await empresasApi.retirarImagenSede(seleccionada.value.id, imagen.id)
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo retirar la imagen.'
  }
}
async function cambiarEstado() {
  if (!window.confirm('¿Quieres cambiar el estado de ' + seleccionada.value.nombre + '?')) return
  try {
    const { data } = await empresasApi.estadoSede(seleccionada.value.id, !seleccionada.value.activa)
    seleccionada.value = data
    sedes.value = sedes.value.map((item) => item.id === data.id ? data : item)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo cambiar el estado.'
  }
}
</script>

<template>
  <AdminLayout :titulo="titulo" descripcion="La información y las acciones están limitadas a las sedes asignadas a tu cuenta.">
    <p v-if="error" role="alert" class="admin-error mb-4">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success mb-4">{{ mensaje }}</p>
    <p v-if="cargando" role="status" class="admin-card">Cargando sedes…</p>
    <section v-else-if="!sedes.length" class="admin-card">
      <h2 class="font-bold">No tienes sedes asignadas.</h2>
      <p class="mt-2 text-sm text-app-text-muted">Pide al dueño de la empresa que revise tu acceso.</p>
    </section>
    <div v-else class="grid items-start gap-5 lg:grid-cols-[280px_minmax(0,1fr)]">
      <nav class="admin-card grid gap-2" aria-label="Sedes autorizadas">
        <button v-for="sede in sedes" :key="sede.id"
          :class="['admin-nav-link', seleccionada?.id === sede.id ? 'admin-nav-link-active' : '']"
          :aria-current="seleccionada?.id === sede.id ? 'page' : undefined"
          @click="seleccionarSede(sede)">
          <span class="min-w-0"><span class="block truncate font-semibold">{{ sede.nombre }}</span><span class="block truncate text-sm text-app-text-muted">{{ sede.distrito || sede.empresa }}</span></span>
          <span class="admin-nav-line" aria-hidden="true" />
        </button>
      </nav>
      <section v-if="seleccionada" class="min-w-0">
        <nav class="mb-4 flex flex-wrap gap-2" aria-label="Administración de sede">
          <button class="admin-button" :class="vista === 'sede' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="vista === 'sede'" @click="vista = 'sede'">Información de sede</button>
          <button class="admin-button" :class="vista === 'canchas' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="vista === 'canchas'" @click="vista = 'canchas'">Canchas</button>
          <button class="admin-button" :class="vista === 'horarios' ? 'admin-button-primary' : 'admin-button-secondary'" type="button" :aria-pressed="vista === 'horarios'" @click="vista = 'horarios'">Horarios</button>
        </nav>
        <GestionCanchasPanel v-if="vista === 'canchas'" :key="'canchas-sede-' + seleccionada.id" :sedes="sedes" :sede-inicial-id="seleccionada.id" :sede-fija="true" />
        <GestionHorariosPanel v-else-if="vista === 'horarios'" :key="'horarios-sede-' + seleccionada.id" :sedes="sedes" :sede-inicial-id="seleccionada.id" :sede-fija="true" />
        <section v-else class="admin-card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div><p class="text-sm text-app-text-muted">{{ seleccionada.empresa }}</p><h2 class="mt-1 text-xl font-bold">{{ seleccionada.nombre }}</h2><p class="mt-1 text-sm text-app-text-muted">{{ seleccionada.direccion }}</p></div>
          <EstadoEtiqueta :estado="seleccionada.activa ? 'activa' : 'suspendida'" />
        </div>
        <div v-if="!editando" class="mt-5 grid gap-4 sm:grid-cols-2">
          <div><p class="text-sm text-app-text-muted">Ubicación</p><p>{{ [seleccionada.distrito, seleccionada.provincia, seleccionada.departamento].filter(Boolean).join(', ') || 'Sin ubicación registrada' }}</p></div>
          <div><p class="text-sm text-app-text-muted">Contacto</p><p class="break-words">{{ seleccionada.telefono_contacto || 'Sin teléfono' }}</p><p class="break-words">{{ seleccionada.correo_contacto || 'Sin correo' }}</p></div>
          <div v-if="seleccionada.latitud && seleccionada.longitud"><p class="text-sm text-app-text-muted">Coordenadas</p><p class="tabular-nums">{{ seleccionada.latitud }}, {{ seleccionada.longitud }}</p></div>
          <p class="text-sm text-app-text-muted sm:col-span-2">{{ seleccionada.descripcion || 'Sin descripción' }}</p>
          <figure v-if="seleccionada.imagen_principal_url" class="sm:col-span-2">
            <img :src="seleccionada.imagen_principal_url" :alt="'Imagen principal de ' + seleccionada.nombre" class="max-h-64 w-full rounded-xl border border-app-border object-cover">
          </figure>
          <div v-if="seleccionada.imagenes?.length" class="flex flex-wrap gap-3 sm:col-span-2">
            <figure v-for="imagen in seleccionada.imagenes" :key="imagen.id" class="relative">
              <img :src="imagen.url" :alt="imagen.descripcion || ('Imagen de ' + seleccionada.nombre)" class="h-20 w-28 rounded-lg border border-app-border object-cover">
              <button class="absolute right-1 top-1 rounded bg-app-surface px-2 py-1 text-xs font-semibold" :aria-label="'Retirar imagen ' + imagen.id" @click="retirarImagen(imagen)">Retirar</button>
            </figure>
          </div>
          <div class="flex flex-wrap items-end gap-2 sm:col-span-2">
            <label class="min-w-52 flex-1"><span class="admin-label">Añadir imagen</span><input class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" @change="elegirImagenGaleria"></label>
            <button class="admin-button admin-button-secondary" :disabled="!imagenGaleria" @click="subirImagenGaleria">Subir imagen</button>
          </div>
          <div class="flex flex-wrap gap-2 sm:col-span-2">
            <button class="admin-button admin-button-primary" @click="editar">Editar información</button>
            <button class="admin-button admin-button-secondary" @click="cambiarEstado">{{ seleccionada.activa ? 'Desactivar sede' : 'Activar sede' }}</button>
          </div>
        </div>
        <form v-else class="mt-5 grid gap-4 sm:grid-cols-2" @submit.prevent="guardar" :aria-busy="guardando">
          <label><span class="admin-label">Nombre</span><input v-model.trim="form.nombre" class="admin-field" required maxlength="160"></label>
          <label><span class="admin-label">Dirección</span><input v-model.trim="form.direccion" class="admin-field" required maxlength="240"></label>
          <label><span class="admin-label">Departamento</span><input v-model.trim="form.departamento" class="admin-field"></label>
          <label><span class="admin-label">Provincia</span><input v-model.trim="form.provincia" class="admin-field"></label>
          <label><span class="admin-label">Distrito</span><input v-model.trim="form.distrito" class="admin-field"></label>
          <label><span class="admin-label">Teléfono</span><input v-model.trim="form.telefono_contacto" class="admin-field" type="tel"></label>
          <label><span class="admin-label">WhatsApp</span><input v-model.trim="form.whatsapp_contacto" class="admin-field" type="tel"></label>
          <label><span class="admin-label">Correo</span><input v-model.trim="form.correo_contacto" class="admin-field" type="email"></label>
          <label class="sm:col-span-2"><span class="admin-label">Descripción</span><textarea v-model.trim="form.descripcion" class="admin-field min-h-24" rows="3" /></label>
          <label><span class="admin-label">Latitud</span><input v-model="form.latitud" class="admin-field" type="number" min="-90" max="90" step="0.000001"></label>
          <label><span class="admin-label">Longitud</span><input v-model="form.longitud" class="admin-field" type="number" min="-180" max="180" step="0.000001"></label>
          <label class="sm:col-span-2"><span class="admin-label">Imagen principal <span class="font-normal text-app-text-muted">(PNG, JPG o WebP; máximo 5 MB)</span></span><input class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" @change="elegirPortada"></label>
          <div class="flex flex-wrap gap-2 sm:col-span-2">
            <button class="admin-button admin-button-primary" :disabled="guardando">{{ guardando ? 'Guardando…' : 'Guardar cambios' }}</button>
            <button class="admin-button admin-button-secondary" type="button" @click="editando = false">Cancelar</button>
          </div>
        </form>
        </section>
      </section>
    </div>
  </AdminLayout>
</template>
