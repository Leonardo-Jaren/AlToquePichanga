<script setup>
import { DIAS_SEMANA, TIPOS_TARIFA, formatearPEN } from '../../utils/tarifas'

defineProps({ reglas: { type: Array, default: () => [] }, soloLectura: Boolean })
const emit = defineEmits(['editar', 'cambiar-estado'])

function tipoNombre(tipo) { return TIPOS_TARIFA.find((item) => item.value === tipo)?.label || tipo }
function diasNombre(dias = []) { return dias.map((dia) => DIAS_SEMANA.find((item) => item.value === dia)?.label).filter(Boolean).join(', ') }
function aplicacion(regla) {
  if (['feriado', 'especial'].includes(regla.tipo)) return `${regla.fecha_aplicable_desde} al ${regla.fecha_aplicable_hasta}`
  if (regla.tipo === 'fin_semana') return 'Sábados y domingos'
  return diasNombre(regla.dias_semana)
}
function horario(regla) { return regla.todo_el_dia ? 'Todo el día' : `${regla.hora_inicio}–${regla.hora_fin}` }
</script>

<template>
  <section class="admin-card" aria-labelledby="lista-tarifas">
    <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div><h3 id="lista-tarifas" class="font-display text-lg">Reglas de precios</h3><p class="mt-1 text-sm text-app-text-muted">El precio depende de la cancha, fecha y hora configuradas.</p></div>
      <span class="rounded-full bg-app-surface-2 px-3 py-1 text-xs font-semibold">{{ reglas.length }} {{ reglas.length === 1 ? 'regla' : 'reglas' }}</span>
    </div>
    <p v-if="!reglas.length" class="rounded-lg bg-app-surface-2 p-4 text-sm text-app-text-muted">Todavía no hay tarifas configuradas. Agrega reglas para mostrar precios en la consulta horaria.</p>
    <ul v-else class="divide-y divide-app-border">
      <li v-for="regla in reglas" :key="regla.id" class="grid gap-3 py-4 sm:grid-cols-[minmax(0,1fr)_auto]">
        <div class="min-w-0">
          <div class="flex flex-wrap items-center gap-2"><h4 class="font-bold">{{ regla.nombre || tipoNombre(regla.tipo) }}</h4><span class="admin-state" :class="regla.activa ? 'admin-state-success' : 'admin-state-warning'">{{ regla.activa ? 'Activa' : 'Inactiva' }}</span></div>
          <p class="mt-1 text-sm text-app-text-muted">{{ tipoNombre(regla.tipo) }} · {{ aplicacion(regla) }} · {{ horario(regla) }}</p>
          <p class="mt-1 text-xs text-app-text-muted">Vigencia: {{ regla.vigente_desde }}{{ regla.vigente_hasta ? ` a ${regla.vigente_hasta}` : ' en adelante' }}</p>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-3 sm:justify-end">
          <strong class="text-lg tabular-nums">{{ formatearPEN(regla.precio_hora, regla.moneda) }}<span class="ml-1 text-xs font-medium text-app-text-muted">/ hora</span></strong>
          <div v-if="!soloLectura" class="flex gap-2">
            <button class="admin-button admin-button-secondary" type="button" @click="emit('editar', regla)">Editar</button>
            <button class="admin-button" :class="regla.activa ? 'admin-button-danger' : 'admin-button-secondary'" type="button" @click="emit('cambiar-estado', regla)">{{ regla.activa ? 'Desactivar' : 'Activar' }}</button>
          </div>
        </div>
      </li>
    </ul>
  </section>
</template>
