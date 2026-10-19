import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { cuenta } from '../services/cuenta'

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

  async function recuperarSesion() {
    if (consulta) return consulta
    consulta = cuenta.perfil().then(({ data }) => {
      usuario.value = data
      return data
    }).catch((error) => {
      if (error.response?.status === 401) {
        usuario.value = null
        return null
      }
      throw error
    }).finally(() => { consulta = null })
    return consulta
  }

  async function ingresar(datos) {
    usuario.value = (await cuenta.ingresar(datos)).data
  }

  async function registrar(datos) {
    usuario.value = (await cuenta.registrar(datos)).data
  }

  async function actualizar(datos) {
    usuario.value = (await cuenta.actualizar(datos)).data
  }

  async function salir() {
    try { await cuenta.salir() } catch (error) {
      if (error.response?.status !== 401) throw error
    }
    usuario.value = null
  }

  return { usuario, autenticado, recuperarSesion, ingresar, registrar, actualizar, salir }
})
