<script setup>
import { onMounted, ref, watch } from 'vue'
import { MapPin } from 'lucide-vue-next'
import { canchasApi } from '@/modules/canchas/services/canchas'
import SelectControl from '@/shared/components/controles/SelectControl.vue'
import { mensajeErrorApi } from '@/modules/tarifas/utils/tarifas'
import MatrizCalendarioAdmin from '../calendario/MatrizCalendarioAdmin.vue'

const props = defineProps({
  sedes: { type: Array, default: () => [] },
  sedeInicialId: { type: [Number, String], default: '' },
  sedeFija: { type: Boolean, default: false },
  cargarSedes: { type: Boolean, default: false },
})

const sedesInternas = ref([])
const sedeId = ref('')
const canchas = ref([])
const cargando = ref(false)
const error = ref('')
let solicitudCanchas = 0
const sedesVisibles = () => props.cargarSedes ? sedesInternas.value : props.sedes

onMounted(iniciar)
watch(() => props.sedeInicialId, (id) => { if (id) seleccionarSede(id) })
watch(() => props.sedes.map((sede) => sede.id).join(','), () => {
  if (!props.cargarSedes && !props.sedeFija
    && !sedesVisibles().some((sede) => String(sede.id) === String(sedeId.value))) {
    sedeId.value = String(sedesVisibles()[0]?.id || '')
    cargarCanchas()
  }
})

async function iniciar() {
  error.value = ''
  if (props.cargarSedes) {
    try {
      const { data } = await canchasApi.listarSedes()
      sedesInternas.value = Array.isArray(data) ? data : data?.results || []
    } catch (fallo) {
      error.value = mensajeErrorApi(fallo, 'No se pudieron cargar las sedes autorizadas.')
      return
    }
  }
  sedeId.value = String(props.sedeInicialId || sedesVisibles()[0]?.id || '')
  await cargarCanchas()
}

async function seleccionarSede(id) {
  if (String(id) === String(sedeId.value)) return
  sedeId.value = String(id)
  await cargarCanchas()
}

async function cargarCanchas() {
  const actual = ++solicitudCanchas
  canchas.value = []
  error.value = ''
  if (!sedeId.value) return
  cargando.value = true
  try {
    const { data } = await canchasApi.listar({ sede: sedeId.value, page_size: 100 })
    if (actual !== solicitudCanchas) return
    const resultados = Array.isArray(data) ? data : data?.results || []
    canchas.value = resultados.filter((cancha) => {
      const idSede = cancha.sede_id ?? (typeof cancha.sede === 'object' ? cancha.sede?.id : cancha.sede)
      return String(idSede) === sedeId.value
    })
  } catch (fallo) {
    if (actual === solicitudCanchas) error.value = mensajeErrorApi(fallo, 'No se pudieron cargar las canchas de esta sede.')
  } finally { if (actual === solicitudCanchas) cargando.value = false }
}
</script>

<template>
  <section class="calendar-admin-panel" aria-labelledby="calendario-admin-titulo">
    <header class="calendar-admin-panel-heading">
      <div>
        <p class="calendar-panel-eyebrow">Programación de canchas</p>
        <h2 id="calendario-admin-titulo">Programación de canchas</h2>
        <p>Horarios, cierres excepcionales y precios de las canchas autorizadas.</p>
      </div>
      <div class="calendar-admin-site-picker">
        <SelectControl v-if="!sedeFija" id="calendario-sede" label="Sede" :model-value="sedeId"
          :options="sedesVisibles().map((sede) => ({ value: String(sede.id), label: sede.nombre }))"
          placeholder="Selecciona una sede" :disabled="cargando || !sedesVisibles().length" @update:model-value="seleccionarSede" />
        <div v-else-if="sedesVisibles().find((sede) => String(sede.id) === sedeId)" class="calendar-fixed-site">
          <span><MapPin aria-hidden="true" />Sede autorizada</span>
          <strong>{{ sedesVisibles().find((sede) => String(sede.id) === sedeId)?.nombre }}</strong>
        </div>
      </div>
    </header>

    <p v-if="error" class="admin-error" role="alert">{{ error }}</p>
    <p v-if="cargando" class="admin-card calendar-panel-loading" role="status">Cargando canchas de la sede…</p>
    <section v-else-if="!sedesVisibles().length" class="admin-card calendar-panel-empty">
      <h3>No hay sedes para consultar</h3><p>Las sedes autorizadas aparecerán aquí.</p>
    </section>
    <section v-else-if="sedeId && !canchas.length" class="admin-card calendar-panel-empty">
      <h3>Esta sede aún no tiene canchas</h3><p>Agrega una cancha desde la sección Canchas para consultar su calendario.</p>
    </section>
    <MatrizCalendarioAdmin v-else-if="canchas.length" :key="`matriz-${sedeId}`" :canchas="canchas" />
  </section>
</template>

<style scoped>
.calendar-admin-panel { display: grid; gap: 18px; min-width: 0; }
.calendar-admin-panel-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; }
.calendar-panel-eyebrow { margin: 0 0 5px; color: var(--link); font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.calendar-admin-panel-heading h2 { margin: 0; color: var(--text); font: 700 20px/1.3 var(--font-body); }
.calendar-admin-panel-heading p:last-child { margin: 5px 0 0; color: var(--text-muted); font-size: 14px; }
.calendar-admin-site-picker { width: min(100%, 340px); }
.calendar-fixed-site { display: grid; gap: 5px; }
.calendar-fixed-site > span { display: flex; align-items: center; gap: 6px; color: var(--text-muted); font-size: 12px; font-weight: 600; }
.calendar-fixed-site svg { height: 15px; width: 15px; }
.calendar-fixed-site strong { display: grid; min-height: 44px; align-items: center; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--surface-2); padding: 8px 12px; font-size: 14px; }
.calendar-panel-loading { color: var(--text-muted); }
.calendar-panel-empty h3 { margin: 0; font-size: 16px; font-weight: 700; }
.calendar-panel-empty p { margin: 6px 0 0; color: var(--text-muted); font-size: 14px; }
@media (max-width: 639px) {
  .calendar-admin-panel-heading { align-items: stretch; flex-direction: column; gap: 14px; }
  .calendar-admin-site-picker { width: 100%; }
}
</style>
