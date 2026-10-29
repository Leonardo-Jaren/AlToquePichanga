import { computed, onUnmounted, ref, unref, watch } from 'vue'
import api from '@/shared/services/api'

const ESPERAS_MS = [1000, 2000, 4000, 8000, 15000]
const CODIGOS_SIN_REINTENTO = new Set([4400, 4401, 4403])

function normalizarIds(valor) {
  const lista = Array.isArray(valor) ? valor : String(valor || '').split(',')
  return [...new Set(lista.map((item) => String(item?.id ?? item).trim()).filter(Boolean))]
    .sort((a, b) => Number(a) - Number(b))
}

function urlWebSocket(ids, desde, hasta) {
  const url = new URL(api.defaults?.baseURL || 'http://localhost:8000/api')
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `${url.pathname.replace(/\/api\/?$/, '').replace(/\/$/, '')}/ws/disponibilidad/`
  url.search = new URLSearchParams({ canchas: ids.join(','), desde, hasta }).toString()
  return url.toString()
}

export function useDisponibilidadTiempoReal({ canchas, desde, hasta, alCambiar, alRecuperar }) {
  const estado = ref('conectando')
  const sincronizadoEn = ref('')
  const ids = computed(() => normalizarIds(unref(canchas)))
  let socket = null
  let temporizadorReconexion = null
  let temporizadorEstable = null
  let intentos = 0
  let conectoAlgunaVez = false
  let desmontado = false

  function limpiarTemporizadores() {
    clearTimeout(temporizadorReconexion)
    clearTimeout(temporizadorEstable)
    temporizadorReconexion = null
    temporizadorEstable = null
  }

  function cerrarSocket() {
    if (!socket) return
    const anterior = socket
    socket = null
    anterior.onopen = null
    anterior.onmessage = null
    anterior.onerror = null
    anterior.onclose = null
    if (anterior.readyState < WebSocket.CLOSING) anterior.close(1000, 'Suscripción actualizada')
  }

  function marcarConsultaExitosa() {
    sincronizadoEn.value = new Date().toLocaleTimeString('es-PE', {
      hour: '2-digit', minute: '2-digit', hour12: false,
    })
  }

  function recibir(evento) {
    let datos
    try { datos = JSON.parse(evento.data) } catch { return }
    if (datos?.tipo !== 'disponibilidad_actualizada' || !ids.value.includes(String(datos.cancha_id))) return
    const inicio = unref(desde)
    const fin = unref(hasta)
    if (datos.fecha && (datos.fecha < inicio || datos.fecha > fin)) return
    alCambiar?.(datos)
  }

  function conectar() {
    if (desmontado || !ids.value.length || !unref(desde) || !unref(hasta)) return
    if (typeof WebSocket === 'undefined') {
      estado.value = 'desconectado'
      return
    }
    limpiarTemporizadores()
    cerrarSocket()
    estado.value = intentos ? 'reconectando' : 'conectando'
    let siguiente
    try { siguiente = new WebSocket(urlWebSocket(ids.value, unref(desde), unref(hasta))) } catch {
      programarReconexion()
      return
    }
    socket = siguiente
    siguiente.onopen = () => {
      if (socket !== siguiente || desmontado) return
      estado.value = 'conectado'
      if (conectoAlgunaVez) alRecuperar?.()
      conectoAlgunaVez = true
      temporizadorEstable = setTimeout(() => { intentos = 0 }, 30000)
    }
    siguiente.onmessage = (evento) => { if (socket === siguiente) recibir(evento) }
    siguiente.onerror = () => { if (socket === siguiente) estado.value = 'reconectando' }
    siguiente.onclose = (evento) => {
      if (socket !== siguiente || desmontado) return
      socket = null
      if (evento.code === 1000) return
      if (CODIGOS_SIN_REINTENTO.has(evento.code)) {
        intentos = ESPERAS_MS.length
        estado.value = 'desconectado'
        return
      }
      programarReconexion()
    }
  }

  function programarReconexion() {
    limpiarTemporizadores()
    if (intentos >= ESPERAS_MS.length) {
      estado.value = 'desconectado'
      return
    }
    estado.value = 'reconectando'
    const espera = ESPERAS_MS[intentos]
    intentos += 1
    temporizadorReconexion = setTimeout(conectar, espera)
  }

  watch(
    () => [ids.value.join(','), unref(desde), unref(hasta)],
    () => {
      limpiarTemporizadores()
      cerrarSocket()
      intentos = 0
      conectoAlgunaVez = false
      sincronizadoEn.value = ''
      if (ids.value.length) conectar()
      else estado.value = 'desconectado'
    },
    { immediate: true },
  )

  onUnmounted(() => {
    desmontado = true
    limpiarTemporizadores()
    cerrarSocket()
  })

  return { estado, sincronizadoEn, marcarConsultaExitosa }
}
