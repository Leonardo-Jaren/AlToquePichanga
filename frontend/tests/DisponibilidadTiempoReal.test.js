import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, nextTick, ref } from 'vue'
import { mount } from '@vue/test-utils'
import { useDisponibilidadTiempoReal } from '@/modules/calendario/composables/useDisponibilidadTiempoReal'
import EstadoDisponibilidadTiempoReal from '@/modules/calendario/components/calendario/EstadoDisponibilidadTiempoReal.vue'

const sockets = []

class WebSocketPrueba {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  constructor(url) {
    this.url = url
    this.readyState = WebSocketPrueba.CONNECTING
    sockets.push(this)
  }

  open() {
    this.readyState = WebSocketPrueba.OPEN
    this.onopen?.({})
  }

  enviar(datos) { this.onmessage?.({ data: JSON.stringify(datos) }) }

  close(code = 1000) {
    this.readyState = WebSocketPrueba.CLOSED
    this.onclose?.({ code })
  }
}

function montar(onCambiar = vi.fn(), onRecuperar = vi.fn()) {
  const ids = ref([15])
  const desde = ref('2026-10-26')
  const hasta = ref('2026-10-26')
  const componente = defineComponent({
    setup() {
      const realtime = useDisponibilidadTiempoReal({
        canchas: ids, desde, hasta, alCambiar: onCambiar, alRecuperar: onRecuperar,
      })
      return { ids, desde, hasta, realtime }
    },
    template: '<div />',
  })
  const wrapper = mount(componente)
  return { wrapper, ids, desde, hasta, onCambiar, onRecuperar }
}

describe('useDisponibilidadTiempoReal', () => {
  beforeEach(() => {
    sockets.length = 0
    vi.stubGlobal('WebSocket', WebSocketPrueba)
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('abre una suscripción de cancha/fecha, filtra eventos y recuerda la consulta REST', () => {
    const datos = vi.fn()
    const { wrapper } = montar(datos)
    const socket = sockets[0]
    const url = new URL(socket.url)
    expect(url.pathname).toBe('/ws/disponibilidad/')
    expect(url.searchParams.get('canchas')).toBe('15')
    expect(url.searchParams.get('desde')).toBe('2026-10-26')

    socket.open()
    expect(wrapper.vm.realtime.estado.value).toBe('conectado')
    socket.enviar({ tipo: 'disponibilidad_actualizada', cancha_id: 15, fecha: '2026-10-26' })
    socket.enviar({ tipo: 'disponibilidad_actualizada', cancha_id: 99, fecha: '2026-10-26' })
    socket.enviar({ tipo: 'otra_cosa', cancha_id: 15, fecha: '2026-10-26' })
    expect(datos).toHaveBeenCalledTimes(1)

    wrapper.vm.realtime.marcarConsultaExitosa()
    expect(wrapper.vm.realtime.sincronizadoEn.value).toMatch(/^\d{2}:\d{2}$/)
    wrapper.unmount()
  })

  it('reemplaza la conexión al cambiar cancha o fecha', async () => {
    const { wrapper, ids, desde, hasta } = montar()
    const anterior = sockets[0]
    ids.value = [22]
    desde.value = '2026-10-27'
    hasta.value = '2026-10-27'
    await nextTick()
    expect(anterior.readyState).toBe(WebSocketPrueba.CLOSED)
    expect(sockets).toHaveLength(2)
    expect(new URL(sockets[1].url).searchParams.get('canchas')).toBe('22')
    expect(new URL(sockets[1].url).searchParams.get('desde')).toBe('2026-10-27')
    wrapper.unmount()
  })

  it('reconecta con esperas progresivas, sincroniza al recuperar y limita intentos', async () => {
    const recuperar = vi.fn()
    const { wrapper } = montar(vi.fn(), recuperar)
    sockets[0].open()
    sockets[0].close(1006)
    expect(wrapper.vm.realtime.estado.value).toBe('reconectando')
    await vi.advanceTimersByTimeAsync(999)
    expect(sockets).toHaveLength(1)
    await vi.advanceTimersByTimeAsync(1)
    expect(sockets).toHaveLength(2)
    sockets[1].open()
    expect(recuperar).toHaveBeenCalledTimes(1)
    wrapper.unmount()

    sockets.length = 0
    const otro = montar()
    for (const espera of [1000, 2000, 4000, 8000, 15000]) {
      sockets.at(-1).close(1006)
      await vi.advanceTimersByTimeAsync(espera)
    }
    sockets.at(-1).close(1006)
    expect(otro.wrapper.vm.realtime.estado.value).toBe('desconectado')
    expect(sockets).toHaveLength(6)
    otro.wrapper.unmount()
  })

  it('no reintenta una suscripción rechazada y cierra al desmontar', async () => {
    const { wrapper } = montar()
    sockets[0].close(4403)
    expect(wrapper.vm.realtime.estado.value).toBe('desconectado')
    await vi.advanceTimersByTimeAsync(30000)
    expect(sockets).toHaveLength(1)
    wrapper.unmount()
    expect(sockets[0].readyState).toBe(WebSocketPrueba.CLOSED)
  })

  it('muestra el estado con los tokens semánticos en tema claro y oscuro', async () => {
    const wrapper = mount(EstadoDisponibilidadTiempoReal, {
      props: { estado: 'desconectado', sincronizadoEn: '19:30' },
    })
    for (const tema of ['light', 'dark']) {
      document.documentElement.dataset.theme = tema
      await nextTick()
      expect(wrapper.get('[role="status"]').attributes('data-state')).toBe('desconectado')
      expect(wrapper.text()).toContain('actualiza antes de elegir un horario')
    }
    delete document.documentElement.dataset.theme
    wrapper.unmount()
  })
})
