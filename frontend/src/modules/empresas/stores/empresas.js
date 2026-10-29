import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { empresasApi } from '../services/empresas'

const CLAVE_EMPRESA = 'altoque.empresa-activa'

export const useEmpresasStore = defineStore('empresas', () => {
  const lista = ref([])
  const activaId = ref(Number(localStorage.getItem(CLAVE_EMPRESA)) || null)
  const cargando = ref(false)
  const error = ref('')
  const empresaActiva = computed(() => lista.value.find((item) => item.id === activaId.value) || null)

  async function cargar() {
    cargando.value = true
    error.value = ''
    try {
      const { data: primera } = await empresasApi.listar({ page: 1, page_size: 100 })
      lista.value = primera.results
      const paginas = Math.ceil(primera.count / 100)
      for (let page = 2; page <= paginas; page += 1) {
        const { data } = await empresasApi.listar({ page, page_size: 100 })
        lista.value.push(...data.results)
      }
      if (!lista.value.some((item) => item.id === activaId.value)) {
        seleccionar(lista.value[0]?.id || null)
      }
      return lista.value
    } catch {
      error.value = 'No se pudieron cargar tus empresas.'
      throw new Error(error.value)
    } finally {
      cargando.value = false
    }
  }

  function seleccionar(id) {
    activaId.value = id ? Number(id) : null
    if (activaId.value) localStorage.setItem(CLAVE_EMPRESA, String(activaId.value))
    else localStorage.removeItem(CLAVE_EMPRESA)
  }

  function limpiar() {
    lista.value = []
    cargando.value = false
    error.value = ''
    seleccionar(null)
  }

  async function registrar(datos) {
    const { data } = await empresasApi.registrar(datos)
    lista.value = [...lista.value, data]
    seleccionar(data.id)
    return data
  }

  async function refrescarActiva() {
    if (!activaId.value) return null
    const { data } = await empresasApi.detalle(activaId.value)
    lista.value = lista.value.map((item) => item.id === data.id ? data : item)
    return data
  }

  return { lista, activaId, empresaActiva, cargando, error, cargar, seleccionar, limpiar, registrar, refrescarActiva }
})
