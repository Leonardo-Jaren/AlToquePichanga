import { nextTick, reactive, ref } from 'vue'

export function useFormulario(iniciales = {}) {
  const datos = reactive({ ...iniciales })
  const errores = ref({})
  const mensaje = ref('')
  const ocupado = ref(false)

  function validar() {
    const resultado = {}
    for (const [campo, valor] of Object.entries(datos)) {
      if (campo === 'apellidos') continue
      if (!valor?.trim()) resultado[campo] = 'Completa este campo.'
    }
    if (datos.correo && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(datos.correo)) {
      resultado.correo = 'Ingresa un correo válido.'
    }
    if ('confirmacion' in datos && datos.confirmacion !== datos.contrasena) {
      resultado.confirmacion = 'Las contraseñas no coinciden.'
    }
    errores.value = resultado
    return Object.keys(resultado).length === 0
  }

  async function ejecutar(accion, validarDatos = true) {
    if (ocupado.value) return false
    mensaje.value = ''
    if (validarDatos && !validar()) {
      await enfocarError()
      return false
    }
    ocupado.value = true
    try {
      await accion()
      return true
    } catch (error) {
      const respuesta = error.response?.data
      if (respuesta && typeof respuesta === 'object' && !Array.isArray(respuesta)) {
        errores.value = Object.fromEntries(Object.entries(respuesta)
          .filter(([campo]) => campo in datos)
          .map(([campo, valor]) => [campo, Array.isArray(valor) ? valor.join(' ') : String(valor)]))
      }
      mensaje.value = typeof respuesta?.detail === 'string' ? respuesta.detail
        : Array.isArray(respuesta) ? respuesta.join(' ')
        : 'No se pudo completar la solicitud. Revisa los datos e intenta nuevamente.'
      await enfocarError()
      return false
    } finally { ocupado.value = false }
  }

  async function enfocarError() {
    await nextTick()
    document.querySelector('[aria-invalid="true"]')?.focus()
  }

  return { datos, errores, mensaje, ocupado, ejecutar }
}
