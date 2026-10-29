import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { cuenta } from '../services/cuenta'
import { useEmpresasStore } from '@/modules/empresas/stores/empresas'

export function puedeAcceder(usuario, rol) {
  if (!usuario) return false
  if (rol === 'plataforma') return usuario.es_superadministrador === true
  if (rol === 'jugador') return usuario.es_jugador === true
  return usuario.membresias.some((m) => m.rol === rol)
}

export function destinoUsuario(usuario) {
  const roles = ['plataforma', 'dueno', 'administrador_sede', 'cajero', 'jugador']
  return `/panel/${roles.find((rol) => puedeAcceder(usuario, rol)) || 'jugador'}`
}

export const useAutenticacionStore = defineStore('autenticacion', () => {
  const usuario = ref(null)
  const autenticado = computed(() => usuario.value !== null)
  let consulta = null

  function limpiarSesion() {
    usuario.value = null
    useEmpresasStore().limpiar()
  }

  function establecerUsuario(datos) {
    if (usuario.value && usuario.value.id !== datos.id) useEmpresasStore().limpiar()
    usuario.value = datos
  }

  async function recuperarSesion() {
    if (consulta) return consulta
    consulta = cuenta.perfil().then(({ data }) => {
      establecerUsuario(data)
      return data
    }).catch((error) => {
      if (error.response?.status === 401) {
        limpiarSesion()
        return null
      }
      throw error
    }).finally(() => { consulta = null })
    return consulta
  }

  async function ingresar(datos) {
    const { data } = await cuenta.ingresar(datos)
    useEmpresasStore().limpiar()
    usuario.value = data
  }

  async function registrar(datos) {
    const { data } = await cuenta.registrar(datos)
    useEmpresasStore().limpiar()
    usuario.value = data
  }

  async function actualizar(datos) {
    establecerUsuario((await cuenta.actualizar(datos)).data)
  }

  async function salir() {
    try { await cuenta.salir() } catch (error) {
      if (error.response?.status !== 401) throw error
    }
    limpiarSesion()
  }

  return { usuario, autenticado, recuperarSesion, ingresar, registrar, actualizar, salir, limpiarSesion }
})
