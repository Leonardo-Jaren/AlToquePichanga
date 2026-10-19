<script setup>
import { computed, reactive, ref } from 'vue'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { empresasApi } from '../services/empresas'

const props = defineProps({
  empresa: { type: Object, required: true },
  suscripcion: { type: Object, default: null },
})
const sedes = ref([])
const cargando = ref(false)
const guardando = ref(false)
const abierto = ref(false)
const editando = ref(null)
const error = ref('')
const mensaje = ref('')
const archivoPrincipal = ref(null)
const archivoGaleria = ref({})
const form = reactive({
  nombre: '', descripcion: '', direccion: '', departamento: '', provincia: '', distrito: '',
  latitud: '', longitud: '', telefono_contacto: '', whatsapp_contacto: '', correo_contacto: '',
})
const puedeCrear = computed(() => props.empresa.activa && props.suscripcion?.estado === 'activa')

async function cargar() {
  cargando.value = true
  error.value = ''
  try {
    const { data } = await empresasApi.listarSedes(props.empresa.id)
    sedes.value = data
  } catch {
    error.value = 'No se pudieron cargar las sedes de esta empresa.'
  } finally {
    cargando.value = false
  }
}
cargar()

function limpiar() {
  Object.assign(form, {
    nombre: '', descripcion: '', direccion: '', departamento: '', provincia: '', distrito: '',
    latitud: '', longitud: '', telefono_contacto: '', whatsapp_contacto: '', correo_contacto: '',
  })
  archivoPrincipal.value = null
  editando.value = null
}
function nuevaSede() { limpiar(); abierto.value = true }
function editar(sede) {
  Object.assign(form, sede)
  archivoPrincipal.value = null
  editando.value = sede.id
  abierto.value = true
}
function elegirPortada(evento) { archivoPrincipal.value = evento.target.files?.[0] || null }
function elegirGaleria(id, evento) { archivoGaleria.value[id] = evento.target.files?.[0] || null }

async function guardar() {
  guardando.value = true
  error.value = ''
  mensaje.value = ''
  try {
    const datos = {
      ...form,
      latitud: form.latitud || null,
      longitud: form.longitud || null,
    }
    let sede = editando.value
      ? (await empresasApi.actualizarSede(editando.value, datos)).data
      : (await empresasApi.crearSede({ ...datos, empresa_id: props.empresa.id })).data
    if (archivoPrincipal.value) {
      const envio = new FormData()
      envio.append('imagen_principal', archivoPrincipal.value)
      sede = (await empresasApi.actualizarSede(sede.id, envio)).data
    }
    sedes.value = editando.value
      ? sedes.value.map((item) => item.id === sede.id ? { ...item, ...sede } : item)
      : [sede, ...sedes.value]
    abierto.value = false
    limpiar()
    mensaje.value = 'Sede guardada.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || Object.values(fallo.response?.data || {}).flat()[0]
      || 'No se pudo guardar la sede. Revisa la información y vuelve a intentarlo.'
  } finally {
    guardando.value = false
  }
}

async function cambiarEstado(sede) {
  const accion = sede.activa ? 'desactivar' : 'activar'
  if (!window.confirm('¿Quieres ' + accion + ' la sede ' + sede.nombre + '?')) return
  error.value = ''
  try {
    const { data } = await empresasApi.estadoSede(sede.id, !sede.activa)
    sedes.value = sedes.value.map((item) => item.id === sede.id ? data : item)
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo actualizar el estado de la sede.'
  }
}

async function subirGaleria(sede) {
  const archivo = archivoGaleria.value[sede.id]
  if (!archivo) return
  try {
    await empresasApi.imagenSede(sede.id, archivo)
    archivoGaleria.value[sede.id] = null
    await cargar()
    mensaje.value = 'Imagen añadida a ' + sede.nombre + '.'
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo subir la imagen.'
  }
}
async function retirarImagen(sede, imagen) {
  if (!window.confirm('¿Quieres retirar esta imagen de la sede?')) return
  try {
    await empresasApi.retirarImagenSede(sede.id, imagen.id)
    await cargar()
  } catch (fallo) {
    error.value = fallo.response?.data?.detail || 'No se pudo retirar la imagen.'
  }
}
</script>

<template>
  <section class="space-y-5" aria-labelledby="sedes-titulo">
    <div class="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h2 id="sedes-titulo" class="text-xl font-bold">Sedes</h2>
        <p class="mt-1 text-sm text-app-text-muted">{{ sedes.length }} sedes registradas en {{ empresa.nombre_comercial || empresa.razon_social }}.</p>
      </div>
      <button class="admin-button admin-button-primary" :disabled="!puedeCrear" @click="nuevaSede">Agregar sede</button>
    </div>
    <p v-if="!puedeCrear" class="admin-error">La empresa debe estar aprobada y tener una suscripción vigente para crear o editar sedes.</p>
    <p v-if="error" role="alert" class="admin-error">{{ error }}</p>
    <p v-if="mensaje" role="status" class="admin-success">{{ mensaje }}</p>
    <p v-if="cargando" role="status" class="text-sm text-app-text-muted">Cargando sedes…</p>
    <div v-else-if="!sedes.length" class="admin-card">
      <p class="font-semibold">Todavía no hay sedes registradas.</p>
      <p class="mt-1 text-sm text-app-text-muted">Cuando se active tu plan, podrás agregar la primera sede.</p>
    </div>
    <div v-else class="grid gap-4 xl:grid-cols-2">
      <article v-for="sede in sedes" :key="sede.id" class="admin-card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="flex flex-wrap items-center gap-2">
              <h3 class="text-lg font-bold">{{ sede.nombre }}</h3>
              <EstadoEtiqueta :estado="sede.activa ? 'activa' : 'suspendida'" />
            </div>
            <p class="mt-1 text-sm text-app-text-muted">{{ [sede.distrito, sede.provincia, sede.departamento].filter(Boolean).join(', ') }}</p>
          </div>
          <div class="flex gap-2">
            <button class="admin-button admin-button-secondary" :disabled="!puedeCrear" @click="editar(sede)">Editar</button>
            <button class="admin-button admin-button-quiet" @click="cambiarEstado(sede)">{{ sede.activa ? 'Desactivar' : 'Activar' }}</button>
          </div>
        </div>
        <p class="mt-4 text-sm">{{ sede.direccion }}</p>
        <p v-if="sede.telefono_contacto || sede.correo_contacto" class="mt-2 break-words text-sm text-app-text-muted">
          {{ sede.telefono_contacto }}<span v-if="sede.telefono_contacto && sede.correo_contacto"> · </span>{{ sede.correo_contacto }}
        </p>
        <div v-if="sede.imagenes?.length" class="mt-4 flex flex-wrap gap-3">
          <figure v-for="imagen in sede.imagenes" :key="imagen.id" class="relative">
            <img :src="imagen.url" :alt="imagen.descripcion || ('Imagen de ' + sede.nombre)" class="h-20 w-28 rounded-lg border border-app-border object-cover">
            <button class="absolute right-1 top-1 rounded bg-app-surface px-2 py-1 text-xs font-semibold" :aria-label="'Retirar imagen ' + imagen.id" @click="retirarImagen(sede, imagen)">Retirar</button>
          </figure>
        </div>
        <div class="mt-4 flex flex-wrap items-end gap-2">
          <label class="min-w-52 flex-1">
            <span class="admin-label">Añadir imagen</span>
            <input class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" @change="elegirGaleria(sede.id, $event)">
          </label>
          <button class="admin-button admin-button-secondary" :disabled="!archivoGaleria[sede.id]" @click="subirGaleria(sede)">Subir</button>
        </div>
      </article>
    </div>

    <form v-if="abierto" class="admin-card grid gap-4 md:grid-cols-2" novalidate :aria-busy="guardando" @submit.prevent="guardar">
      <div class="md:col-span-2">
        <h3 class="text-lg font-bold">{{ editando ? 'Editar sede' : 'Nueva sede' }}</h3>
        <p class="mt-1 text-sm text-app-text-muted">Los campos con * son obligatorios.</p>
      </div>
      <label><span class="admin-label">Nombre *</span><input v-model.trim="form.nombre" class="admin-field" required maxlength="160"></label>
      <label><span class="admin-label">Dirección *</span><input v-model.trim="form.direccion" class="admin-field" required maxlength="240"></label>
      <label><span class="admin-label">Departamento</span><input v-model.trim="form.departamento" class="admin-field"></label>
      <label><span class="admin-label">Provincia</span><input v-model.trim="form.provincia" class="admin-field"></label>
      <label><span class="admin-label">Distrito</span><input v-model.trim="form.distrito" class="admin-field"></label>
      <label><span class="admin-label">Teléfono</span><input v-model.trim="form.telefono_contacto" class="admin-field" type="tel"></label>
      <label><span class="admin-label">WhatsApp</span><input v-model.trim="form.whatsapp_contacto" class="admin-field" type="tel"></label>
      <label><span class="admin-label">Correo</span><input v-model.trim="form.correo_contacto" class="admin-field" type="email"></label>
      <label><span class="admin-label">Latitud <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="form.latitud" class="admin-field" inputmode="decimal"></label>
      <label><span class="admin-label">Longitud <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="form.longitud" class="admin-field" inputmode="decimal"></label>
      <label class="md:col-span-2"><span class="admin-label">Descripción</span><textarea v-model.trim="form.descripcion" class="admin-field min-h-24" rows="3" /></label>
      <label class="md:col-span-2"><span class="admin-label">Imagen principal <span class="font-normal text-app-text-muted">(PNG, JPG o WebP; máximo 5 MB)</span></span>
        <input class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" @change="elegirPortada"></label>
      <p v-if="error" role="alert" class="admin-error md:col-span-2">{{ error }}</p>
      <div class="flex flex-wrap gap-2 md:col-span-2">
        <button class="admin-button admin-button-primary" :disabled="guardando">{{ guardando ? 'Guardando…' : 'Guardar sede' }}</button>
        <button class="admin-button admin-button-secondary" type="button" :disabled="guardando" @click="abierto = false; limpiar()">Cancelar</button>
      </div>
    </form>
  </section>
</template>
