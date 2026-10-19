<script setup>
import { computed, ref, watch } from 'vue'
import { ImagePlus, Pencil, Trash2, Upload } from 'lucide-vue-next'
import EstadoEtiqueta from '@/modules/administracion/components/EstadoEtiqueta.vue'
import { errorImagenCancha } from '../utils/imagenes'

const props = defineProps({
  cancha: { type: Object, required: true },
  sedeNombre: { type: String, default: '' },
  soloLectura: { type: Boolean, default: false },
  subiendoImagen: { type: Boolean, default: false },
  retirandoImagenId: { type: [Number, String], default: null },
})
const emit = defineEmits(['editar', 'estado', 'subir-imagen', 'retirar-imagen'])
const estadoNuevo = ref(props.cancha.estado || 'activa')
const archivo = ref(null)
const descripcionImagen = ref('')
const errorImagen = ref('')
const estados = [
  { value: 'activa', label: 'Activa' },
  { value: 'inactiva', label: 'Inactiva' },
  { value: 'mantenimiento', label: 'Mantenimiento' },
]
const caracteristicas = computed(() => {
  if (Array.isArray(props.cancha.caracteristicas)) return props.cancha.caracteristicas
  return String(props.cancha.caracteristicas || '').split(/[\n,]/).map((item) => item.trim()).filter(Boolean)
})
const fotos = computed(() => props.cancha.imagenes || [])

watch(() => props.cancha.estado, (estado) => { estadoNuevo.value = estado || 'activa' })

function seleccionarArchivo(evento) {
  errorImagen.value = ''
  const elegido = evento.target.files?.[0] || null
  const errorArchivo = errorImagenCancha(elegido)
  if (errorArchivo) {
    errorImagen.value = errorArchivo
    evento.target.value = ''
    archivo.value = null
    return
  }
  archivo.value = elegido
}

function subirImagen() {
  if (!archivo.value) return
  emit('subir-imagen', {
    cancha: props.cancha,
    archivo: archivo.value,
    descripcion: descripcionImagen.value,
    orden: fotos.value.length,
  })
}
</script>

<template>
  <article class="admin-card grid content-start gap-4 border-l-2 border-l-brand-lime" :aria-labelledby="`cancha-${cancha.id}-nombre`">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div class="min-w-0">
        <p class="text-sm text-app-text-muted">{{ sedeNombre || 'Sede autorizada' }}</p>
        <h3 :id="`cancha-${cancha.id}-nombre`" class="mt-1 break-words text-lg font-bold">{{ cancha.nombre }}</h3>
      </div>
      <EstadoEtiqueta :estado="cancha.estado" />
    </div>

    <figure v-if="cancha.imagen_principal_url" class="overflow-hidden rounded-xl border border-app-border bg-app-surface-2">
      <img :src="cancha.imagen_principal_url" :alt="`Imagen principal de ${cancha.nombre}`" class="h-44 w-full object-cover" loading="lazy">
    </figure>
    <div v-else class="flex h-36 items-center justify-center rounded-xl border border-dashed border-app-border-strong bg-app-surface-2 text-sm text-app-text-muted">
      <ImagePlus aria-hidden="true" class="mr-2 size-5" />Sin imagen principal
    </div>

    <p v-if="cancha.descripcion" class="text-sm text-app-text-muted">{{ cancha.descripcion }}</p>
    <dl class="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
      <div><dt class="text-app-text-muted">Modalidad</dt><dd class="font-semibold tabular-nums">Fútbol {{ cancha.modalidad }}</dd></div>
      <div><dt class="text-app-text-muted">Superficie</dt><dd class="font-semibold">{{ cancha.tipo_superficie }}</dd></div>
      <div><dt class="text-app-text-muted">Capacidad recomendada</dt><dd class="font-semibold tabular-nums">{{ cancha.capacidad_jugadores ? `${cancha.capacidad_jugadores} jugadores` : 'No especificada' }}</dd></div>
      <div><dt class="text-app-text-muted">Instalaciones</dt><dd class="font-semibold">{{ cancha.techada ? 'Techada' : 'Al aire libre' }} · {{ cancha.iluminacion ? 'Con iluminación' : 'Sin iluminación' }}</dd></div>
    </dl>
    <ul v-if="caracteristicas.length" class="flex flex-wrap gap-2" aria-label="Características adicionales">
      <li v-for="(caracteristica, indice) in caracteristicas" :key="`${cancha.id}-${indice}`" class="rounded-lg border border-app-border bg-app-surface-2 px-2.5 py-1.5 text-sm">{{ caracteristica }}</li>
    </ul>

    <section v-if="fotos.length" class="border-t border-app-border pt-4" :aria-label="`Galería de ${cancha.nombre}`">
      <h4 class="mb-3 text-sm font-bold">Fotografías</h4>
      <ul class="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <li v-for="(imagen, indice) in fotos" :key="imagen.id" class="relative min-w-0">
          <img :src="imagen.url" :alt="imagen.descripcion || `Fotografía ${indice + 1} de ${cancha.nombre}`" class="h-24 w-full rounded-lg border border-app-border object-cover" loading="lazy">
          <button v-if="!soloLectura" class="absolute right-1 top-1 admin-button admin-button-quiet min-h-11 px-2" type="button" :disabled="retirandoImagenId === imagen.id" :aria-label="`Retirar fotografía ${indice + 1} de ${cancha.nombre}`" @click="emit('retirar-imagen', { cancha, imagen })">
            <Trash2 aria-hidden="true" class="size-4" />
          </button>
        </li>
      </ul>
    </section>

    <p v-if="errorImagen" class="text-sm text-[var(--status-danger-text)]" role="alert">{{ errorImagen }}</p>
    <form v-if="!soloLectura" class="grid gap-3 border-t border-app-border pt-4" @submit.prevent="subirImagen">
      <label>
        <span class="admin-label">Añadir fotografía <span class="font-normal text-app-text-muted">(PNG, JPG o WebP, máximo 5 MB)</span></span>
        <input class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" :disabled="subiendoImagen" @change="seleccionarArchivo">
      </label>
      <label>
        <span class="admin-label">Descripción de la imagen (opcional)</span>
        <input v-model.trim="descripcionImagen" class="admin-field" maxlength="180" :disabled="subiendoImagen">
      </label>
      <button class="admin-button admin-button-secondary justify-self-start" type="submit" :disabled="!archivo || subiendoImagen">
        <Upload aria-hidden="true" class="size-4" />{{ subiendoImagen ? 'Subiendo…' : 'Subir fotografía' }}
      </button>
    </form>

    <div v-if="!soloLectura" class="grid gap-3 border-t border-app-border pt-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
      <label>
        <span class="admin-label">Cambiar estado operativo</span>
        <select v-model="estadoNuevo" class="admin-field" :aria-label="`Nuevo estado de ${cancha.nombre}`">
          <option v-for="estado in estados" :key="estado.value" :value="estado.value">{{ estado.label }}</option>
        </select>
      </label>
      <div class="flex flex-wrap gap-2">
        <button class="admin-button admin-button-secondary" type="button" :disabled="!estadoNuevo || estadoNuevo === cancha.estado" :aria-label="`Aplicar estado a ${cancha.nombre}`" @click="emit('estado', { cancha, estado: estadoNuevo })">Aplicar estado</button>
        <button class="admin-button admin-button-primary" type="button" :aria-label="`Editar ${cancha.nombre}`" @click="emit('editar', cancha)">
          <Pencil aria-hidden="true" class="size-4" /><span>Editar</span>
        </button>
      </div>
    </div>
  </article>
</template>
