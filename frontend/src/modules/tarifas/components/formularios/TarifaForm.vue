<script setup>
import { computed, reactive, watch } from 'vue'
import SelectControl from '@/shared/components/controles/SelectControl.vue'
import { DIAS_SEMANA, TIPOS_TARIFA, fechaActualLima } from '../../utils/tarifas'

const props = defineProps({ tarifa: { type: Object, default: null }, guardando: Boolean, error: { type: String, default: '' } })
const emit = defineEmits(['guardar', 'cancelar'])
const estado = reactive(estadoInicial())
const errorValidacion = computed(() => validar())
const usaDias = computed(() => ['diurna', 'nocturna'].includes(estado.tipo))
const usaFechas = computed(() => ['feriado', 'especial'].includes(estado.tipo))

watch(() => props.tarifa, (tarifa) => Object.assign(estado, estadoInicial(tarifa)), { immediate: true })

function estadoInicial(tarifa = null) {
  if (!tarifa) return {
    tipo: 'diurna', nombre: '', dias_semana: [0, 1, 2, 3, 4],
    fecha_aplicable_desde: '', fecha_aplicable_hasta: '', hora_inicio: '', hora_fin: '',
    todo_el_dia: false, vigente_desde: fechaActualLima(), vigente_hasta: '', precio_hora: '',
  }
  return {
    tipo: tarifa.tipo, nombre: tarifa.nombre || '', dias_semana: [...(tarifa.dias_semana || [])],
    fecha_aplicable_desde: tarifa.fecha_aplicable_desde || '', fecha_aplicable_hasta: tarifa.fecha_aplicable_hasta || '',
    hora_inicio: tarifa.hora_inicio || '', hora_fin: tarifa.hora_fin || '', todo_el_dia: tarifa.todo_el_dia,
    vigente_desde: tarifa.vigente_desde, vigente_hasta: tarifa.vigente_hasta || '', precio_hora: tarifa.precio_hora,
  }
}

function validar() {
  if (!estado.nombre.trim() && props.tarifa?.nombre) return 'Conserva o edita el nombre de la regla.'
  if (usaDias.value && !estado.dias_semana.length) return 'Selecciona al menos un día de la semana.'
  if (usaFechas.value) {
    if (!estado.fecha_aplicable_desde || !estado.fecha_aplicable_hasta) return 'Indica las fechas a las que se aplica.'
    if (estado.fecha_aplicable_hasta < estado.fecha_aplicable_desde) return 'La fecha final debe ser igual o posterior al inicio.'
  }
  if (!estado.todo_el_dia && (!estado.hora_inicio || !estado.hora_fin || estado.hora_inicio === estado.hora_fin)) return 'Indica un horario válido o marca “Todo el día”.'
  if (!estado.vigente_desde || (estado.vigente_hasta && estado.vigente_hasta < estado.vigente_desde)) return 'Revisa las fechas de vigencia.'
  if (!/^\d{1,8}(?:[.,]\d{1,2})?$/.test(String(estado.precio_hora))) return 'Ingresa un precio positivo con hasta dos decimales.'
  const [entero, decimal = ''] = String(estado.precio_hora).replace(',', '.').split('.')
  if (BigInt(entero) * 100n + BigInt(decimal.padEnd(2, '0') || '0') <= 0n) return 'El precio debe ser mayor que S/ 0.00.'
  return ''
}

function enviar() {
  if (errorValidacion.value) return
  const fecha = usaFechas.value
  emit('guardar', {
    tipo: estado.tipo, nombre: estado.nombre.trim(),
    dias_semana: usaDias.value ? [...estado.dias_semana].sort((a, b) => a - b) : [],
    fecha_aplicable_desde: fecha ? estado.fecha_aplicable_desde : null,
    fecha_aplicable_hasta: fecha ? estado.fecha_aplicable_hasta : null,
    hora_inicio: estado.todo_el_dia ? null : estado.hora_inicio,
    hora_fin: estado.todo_el_dia ? null : estado.hora_fin,
    todo_el_dia: estado.todo_el_dia,
    vigente_desde: estado.vigente_desde, vigente_hasta: estado.vigente_hasta || null,
    precio_hora: String(estado.precio_hora).replace(',', '.'), moneda: 'PEN',
  })
}
</script>

<template>
  <form class="admin-card grid gap-4 sm:grid-cols-2" novalidate :aria-busy="guardando" @submit.prevent="enviar">
    <h3 class="font-display text-lg sm:col-span-2">{{ tarifa ? 'Editar tarifa' : 'Nueva tarifa' }}</h3>
    <SelectControl id="tipo-tarifa" v-model="estado.tipo" label="Tipo de tarifa" :options="TIPOS_TARIFA" />
    <label><span class="admin-label">Nombre para identificarla <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model.trim="estado.nombre" class="admin-field" maxlength="120" placeholder="Por ejemplo, horario nocturno"></label>
    <fieldset v-if="usaDias" class="sm:col-span-2">
      <legend class="admin-label">Días de aplicación</legend>
      <div class="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <label v-for="dia in DIAS_SEMANA" :key="dia.value" class="flex min-h-11 items-center gap-2 rounded-lg border border-app-border px-3 text-sm">
          <input v-model="estado.dias_semana" type="checkbox" :value="dia.value" class="size-4 accent-brand-lime">{{ dia.label }}
        </label>
      </div>
    </fieldset>
    <p v-else-if="estado.tipo === 'fin_semana'" class="rounded-lg bg-app-surface-2 p-3 text-sm text-app-text-muted sm:col-span-2">Esta regla se aplica los sábados y domingos.</p>
    <template v-if="usaFechas">
      <label><span class="admin-label">Fecha de inicio</span><input v-model="estado.fecha_aplicable_desde" class="admin-field" type="date" required></label>
      <label><span class="admin-label">Fecha de fin</span><input v-model="estado.fecha_aplicable_hasta" class="admin-field" type="date" required></label>
    </template>
    <label class="flex items-center gap-3 sm:col-span-2"><input v-model="estado.todo_el_dia" type="checkbox" class="size-4 accent-brand-lime"><span class="text-sm font-semibold">Aplicar todo el día</span></label>
    <template v-if="!estado.todo_el_dia">
      <label><span class="admin-label">Hora de inicio</span><input v-model="estado.hora_inicio" class="admin-field" type="time" required></label>
      <label><span class="admin-label">Hora de fin</span><input v-model="estado.hora_fin" class="admin-field" type="time" required></label>
      <p class="text-xs text-app-text-muted sm:col-span-2">Puedes cruzar la medianoche. La regla se aplica según la hora de inicio de cada bloque.</p>
    </template>
    <label><span class="admin-label">Vigente desde</span><input v-model="estado.vigente_desde" class="admin-field" type="date" required></label>
    <label><span class="admin-label">Vigente hasta <span class="font-normal text-app-text-muted">(opcional)</span></span><input v-model="estado.vigente_hasta" class="admin-field" type="date"></label>
    <label class="sm:col-span-2"><span class="admin-label">Precio por hora (S/)</span><input v-model="estado.precio_hora" class="admin-field" type="text" inputmode="decimal" autocomplete="off" placeholder="0.00" required></label>
    <p v-if="errorValidacion" role="alert" class="admin-error sm:col-span-2">{{ errorValidacion }}</p>
    <p v-if="error" role="alert" class="admin-error sm:col-span-2">{{ error }}</p>
    <div class="flex flex-wrap gap-2 sm:col-span-2">
      <button class="admin-button admin-button-primary" type="submit" :disabled="guardando || Boolean(errorValidacion)">{{ guardando ? 'Guardando…' : 'Guardar tarifa' }}</button>
      <button class="admin-button admin-button-secondary" type="button" :disabled="guardando" @click="emit('cancelar')">Cancelar</button>
    </div>
  </form>
</template>
