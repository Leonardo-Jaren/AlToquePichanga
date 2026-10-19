<script setup>
import { ref } from 'vue'
import AdminLayout from '../components/AdminLayout.vue'
import EmpresasPlataformaPanel from '../components/EmpresasPlataformaPanel.vue'
import PlanesPanel from '../components/PlanesPanel.vue'
import SolicitudesPanel from '../components/SolicitudesPanel.vue'
import ReglaVigenciaPanel from '../components/ReglaVigenciaPanel.vue'
import GestionCanchasPanel from '@/modules/canchas/components/GestionCanchasPanel.vue'
import GestionHorariosPanel from '@/modules/horarios/components/GestionHorariosPanel.vue'

const seccion = ref('empresas')
const menu = [
  { id: 'empresas', nombre: 'Empresas' },
  { id: 'canchas', nombre: 'Canchas' },
  { id: 'horarios', nombre: 'Horarios' },
  { id: 'planes', nombre: 'Planes SaaS' },
  { id: 'solicitudes', nombre: 'Solicitudes' },
  { id: 'vigencia', nombre: 'Vigencia' },
]
const titulos = {
  empresas: ['Plataforma AlToque', 'Estado de empresas, responsables y suscripciones.'],
  canchas: ['Canchas de la plataforma', 'Consulta y administra las instalaciones de todas las empresas.'],
  horarios: ['Horarios de la plataforma', 'Consulta horarios, cierres y disponibilidad operativa de todas las sedes.'],
  planes: ['Planes de plataforma', 'Configura las condiciones comerciales vigentes.'],
  solicitudes: ['Revisión manual', 'Verifica solicitudes de activación y renovación.'],
  vigencia: ['Vigencia y acceso', 'Mantén una sola regla de vencimiento para la plataforma.'],
}
</script>

<template>
  <AdminLayout :titulo="titulos[seccion][0]" :descripcion="titulos[seccion][1]"
    :secciones="menu" :activa="seccion" @cambiar-seccion="seccion = $event">
    <EmpresasPlataformaPanel v-if="seccion === 'empresas'" />
    <GestionCanchasPanel v-else-if="seccion === 'canchas'" :cargar-sedes="true" />
    <GestionHorariosPanel v-else-if="seccion === 'horarios'" :cargar-sedes="true" />
    <PlanesPanel v-else-if="seccion === 'planes'" />
    <SolicitudesPanel v-else-if="seccion === 'solicitudes'" />
    <ReglaVigenciaPanel v-else />
  </AdminLayout>
</template>
