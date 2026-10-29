<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { datosCanchaParaFormulario } from '../services/canchas'
import { errorImagenCancha } from '../utils/imagenes'

const props = defineProps({
  cancha: { type: Object, default: null },
  sedes: { type: Array, default: () => [] },
  sedeInicialId: { type: [Number, String], default: '' },
  sedeFija: { type: Boolean, default: false },
  guardando: { type: Boolean, default: false },
  errores: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['guardar', 'cancelar'])
const form = reactive(datosCanchaParaFormulario())
const imagenPrincipal = ref(null)
const erroresLocales = ref({})
const resumenErrores = ref(null)
const nombresCampos = {
  sede_id: 'Sede', nombre: 'Nombre', descripcion: 'Descripción', modalidad: 'Modalidad',
  tipo_superficie: 'Superficie', capacidad_jugadores: 'Capacidad', techada: 'Techo',
  iluminacion: 'Iluminación', caracteristicas: 'Características', imagen_principal: 'Imagen principal',
}
const erroresResumen = computed(() => {
  const combinados = { ...erroresLocales.value, ...props.errores }
  return Object.entries(combinados)
    .filter(([campo, valor]) => campo !== 'detail' && campo !== 'non_field_errors' && valor)
    .map(([campo, valor]) => ({
      campo,
      nombre: nombresCampos[campo] || campo,
      mensaje: Array.isArray(valor) ? valor.join(' ') : String(valor),
    }))
})
const errorGeneral = computed(() => {
  const valor = props.errores.detail || props.errores.non_field_errors
  return Array.isArray(valor) ? valor.join(' ') : valor || ''
})

watch(() => props.cancha, (cancha) => {
  const datos = datosCanchaParaFormulario(cancha || {})
  if (!cancha) datos.sede_id = props.sedeInicialId || ''
  Object.assign(form, datos)
  imagenPrincipal.value = null
  erroresLocales.value = {}
}, { immediate: true })
watch(() => props.sedeInicialId, (id) => {
  if (!props.cancha && id) form.sede_id = id
})
watch(() => props.errores, async (errores) => {
  if (Object.keys(errores || {}).length) {
    await nextTick()
    resumenErrores.value?.focus()
  }
}, { deep: true })

function errorCampo(campo) {
  const valor = erroresLocales.value[campo] || props.errores[campo]
  return Array.isArray(valor) ? valor.join(' ') : valor || ''
}

function elegirImagen(evento) {
  const archivo = evento.target.files?.[0] || null
  imagenPrincipal.value = null
  erroresLocales.value = { ...erroresLocales.value }
  delete erroresLocales.value.imagen_principal
  const errorArchivo = errorImagenCancha(archivo)
  if (errorArchivo) {
    erroresLocales.value.imagen_principal = errorArchivo
    evento.target.value = ''
    return
  }
  imagenPrincipal.value = archivo
}

function validar() {
  const errores = {}
  if (!form.sede_id) errores.sede_id = 'Selecciona una sede.'
  if (!form.nombre.trim()) errores.nombre = 'Escribe el nombre de la cancha.'
  const modalidad = Number(form.modalidad)
  if (!Number.isInteger(modalidad) || modalidad < 1 || modalidad > 32767) errores.modalidad = 'Indica una modalidad entera entre 1 y 32767.'
  if (!form.tipo_superficie.trim()) errores.tipo_superficie = 'Indica el tipo de superficie.'
  const capacidad = form.capacidad_jugadores === '' ? null : Number(form.capacidad_jugadores)
  if (capacidad !== null && (!Number.isInteger(capacidad) || capacidad < 1 || capacidad > 32767)) errores.capacidad_jugadores = 'Indica una capacidad entera entre 1 y 32767.'
  const caracteristicas = form.caracteristicas.split('\n').map((item) => item.trim()).filter(Boolean)
  if (caracteristicas.length > 30 || caracteristicas.some((item) => item.length > 100)) {
    errores.caracteristicas = 'Usa hasta 30 características de 100 caracteres como máximo cada una.'
  }
  erroresLocales.value = errores
  return Object.keys(errores).length === 0
}

async function guardar() {
  if (!validar()) {
    await nextTick()
    resumenErrores.value?.focus()
    return
  }
  const capacidad = form.capacidad_jugadores === '' ? null : Number(form.capacidad_jugadores)
  emit('guardar', {
    datos: {
      sede_id: Number(form.sede_id),
      nombre: form.nombre.trim(),
      descripcion: form.descripcion.trim(),
      modalidad: Number(form.modalidad),
      tipo_superficie: form.tipo_superficie.trim(),
      capacidad_jugadores: capacidad,
      techada: form.techada,
      iluminacion: form.iluminacion,
      publicada: form.publicada,
      caracteristicas: form.caracteristicas.split('\n').map((item) => item.trim()).filter(Boolean),
    },
    imagenPrincipal: imagenPrincipal.value,
  })
}
</script>

<template>
  <section class="admin-card border-l-2 border-l-brand-lime" aria-labelledby="formulario-cancha-titulo">
    <div class="mb-5 flex items-start justify-between gap-3">
      <div>
        <h3 id="formulario-cancha-titulo" class="text-lg font-bold">{{ cancha ? 'Editar cancha' : 'Nueva cancha' }}</h3>
        <p class="mt-1 text-sm text-app-text-muted">Registra las características y decide si la cancha aparecerá en la consulta pública de horarios.</p>
      </div>
      <button class="admin-button admin-button-quiet shrink-0" type="button" aria-label="Cerrar formulario" :disabled="guardando" @click="emit('cancelar')">
        <X aria-hidden="true" class="size-4" /><span class="hidden sm:inline">Cerrar</span>
      </button>
    </div>

    <div v-if="erroresResumen.length || errorGeneral" ref="resumenErrores" class="admin-error mb-5" role="alert" tabindex="-1" aria-labelledby="errores-cancha-titulo">
      <p id="errores-cancha-titulo" class="font-semibold">Revisa estos datos antes de guardar.</p>
      <p v-if="errorGeneral" class="mt-1">{{ errorGeneral }}</p>
      <ul v-if="erroresResumen.length" class="mt-2 list-inside list-disc">
        <li v-for="item in erroresResumen" :key="item.campo"><a :href="`#cancha-${item.campo}`" class="font-semibold underline">{{ item.nombre }}:</a> {{ item.mensaje }}</li>
      </ul>
    </div>

    <form class="grid gap-4 md:grid-cols-2" novalidate :aria-busy="guardando" @submit.prevent="guardar">
      <label v-if="!sedeFija" class="md:col-span-2">
        <span class="admin-label">Sede *</span>
        <select id="cancha-sede_id" v-model="form.sede_id" class="admin-field" required :aria-invalid="Boolean(errorCampo('sede_id'))" :aria-describedby="errorCampo('sede_id') ? 'error-sede' : undefined">
          <option value="">Selecciona una sede</option>
          <option v-for="sede in sedes" :key="sede.id" :value="sede.id">{{ sede.nombre }}</option>
        </select>
        <span v-if="errorCampo('sede_id')" id="error-sede" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('sede_id') }}</span>
      </label>
      <div v-else class="rounded-lg bg-app-surface-2 px-3 py-2 md:col-span-2">
        <span class="admin-label">Sede asignada</span>
        <p class="text-sm">{{ sedes.find((sede) => Number(sede.id) === Number(form.sede_id))?.nombre || 'Sede autorizada' }}</p>
      </div>

      <label>
        <span class="admin-label">Nombre *</span>
        <input id="cancha-nombre" v-model.trim="form.nombre" class="admin-field" maxlength="160" required :aria-invalid="Boolean(errorCampo('nombre'))" :aria-describedby="errorCampo('nombre') ? 'error-nombre' : undefined">
        <span v-if="errorCampo('nombre')" id="error-nombre" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('nombre') }}</span>
      </label>
      <label>
        <span class="admin-label">Modalidad de fútbol (jugadores) *</span>
        <input id="cancha-modalidad" v-model="form.modalidad" class="admin-field" type="number" min="1" max="32767" step="1" inputmode="numeric" required :aria-invalid="Boolean(errorCampo('modalidad'))" :aria-describedby="errorCampo('modalidad') ? 'error-modalidad' : undefined">
        <span v-if="errorCampo('modalidad')" id="error-modalidad" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('modalidad') }}</span>
      </label>
      <label>
        <span class="admin-label">Tipo de superficie *</span>
        <input id="cancha-tipo_superficie" v-model.trim="form.tipo_superficie" class="admin-field" maxlength="80" placeholder="Sintético, natural, cemento…" required :aria-invalid="Boolean(errorCampo('tipo_superficie'))" :aria-describedby="errorCampo('tipo_superficie') ? 'error-superficie' : undefined">
        <span v-if="errorCampo('tipo_superficie')" id="error-superficie" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('tipo_superficie') }}</span>
      </label>
      <label>
        <span class="admin-label">Capacidad recomendada (jugadores) <span class="font-normal text-app-text-muted">(opcional)</span></span>
        <input id="cancha-capacidad_jugadores" v-model="form.capacidad_jugadores" class="admin-field" type="number" min="1" max="32767" step="1" inputmode="numeric" :aria-invalid="Boolean(errorCampo('capacidad_jugadores'))" :aria-describedby="errorCampo('capacidad_jugadores') ? 'error-capacidad' : undefined">
        <span v-if="errorCampo('capacidad_jugadores')" id="error-capacidad" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('capacidad_jugadores') }}</span>
      </label>
      <label class="md:col-span-2">
        <span class="admin-label">Descripción</span>
        <textarea id="cancha-descripcion" v-model.trim="form.descripcion" class="admin-field min-h-24" rows="3" maxlength="4000" :aria-invalid="Boolean(errorCampo('descripcion'))" :aria-describedby="errorCampo('descripcion') ? 'error-descripcion' : undefined" />
        <span v-if="errorCampo('descripcion')" id="error-descripcion" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('descripcion') }}</span>
      </label>
      <fieldset class="grid gap-2 sm:grid-cols-2 md:col-span-2">
        <legend class="admin-label">Características de la cancha</legend>
        <label class="flex min-h-11 items-center gap-3 rounded-lg border border-app-border px-3">
          <input v-model="form.techada" type="checkbox" class="size-4 accent-[var(--brand-lime)]"><span>Cancha techada</span>
        </label>
        <label class="flex min-h-11 items-center gap-3 rounded-lg border border-app-border px-3">
          <input v-model="form.iluminacion" type="checkbox" class="size-4 accent-[var(--brand-lime)]"><span>Cuenta con iluminación</span>
        </label>
      </fieldset>
      <label class="md:col-span-2">
        <span class="admin-label">Otras características</span>
        <textarea id="cancha-caracteristicas" v-model="form.caracteristicas" class="admin-field min-h-20" rows="3" maxlength="3030" placeholder="Una característica por línea: tribuna, vestuarios…" :aria-invalid="Boolean(errorCampo('caracteristicas'))" :aria-describedby="errorCampo('caracteristicas') ? 'error-caracteristicas' : undefined" />
        <span v-if="errorCampo('caracteristicas')" id="error-caracteristicas" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('caracteristicas') }}</span>
      </label>
      <label class="flex min-h-14 items-start gap-3 rounded-xl border border-app-border bg-app-surface-2 p-3 md:col-span-2">
        <input v-model="form.publicada" type="checkbox" class="mt-1 size-4 accent-[var(--brand-lime)]">
        <span><span class="block font-semibold">Publicar horarios y precios</span><span class="mt-0.5 block text-sm text-app-text-muted">Mostraremos nombre, características, fotos, sede y disponibilidad operativa. No se publican contactos ni datos de administración.</span></span>
      </label>
      <label class="md:col-span-2">
        <span class="admin-label">Imagen principal <span class="font-normal text-app-text-muted">(PNG, JPG o WebP, máximo 5 MB)</span></span>
        <input id="cancha-imagen_principal" class="admin-field" type="file" accept="image/png,image/jpeg,image/webp" @change="elegirImagen" :aria-invalid="Boolean(errorCampo('imagen_principal'))" :aria-describedby="errorCampo('imagen_principal') ? 'error-imagen' : undefined">
        <span v-if="imagenPrincipal" class="mt-1 block text-sm text-app-text-muted">Seleccionada: {{ imagenPrincipal.name }}</span>
        <span v-if="errorCampo('imagen_principal')" id="error-imagen" class="mt-1 block text-sm text-[var(--status-danger-text)]">{{ errorCampo('imagen_principal') }}</span>
      </label>
      <div class="flex flex-wrap gap-2 md:col-span-2">
        <button class="admin-button admin-button-primary" type="submit" :disabled="guardando || !sedes.length">
          {{ guardando ? 'Guardando…' : cancha ? 'Guardar cambios' : 'Registrar cancha' }}
        </button>
        <button class="admin-button admin-button-secondary" type="button" :disabled="guardando" @click="emit('cancelar')">Cancelar</button>
      </div>
    </form>
  </section>
</template>
