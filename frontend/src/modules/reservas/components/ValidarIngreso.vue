<script setup>
import { onBeforeUnmount, ref } from 'vue'
import BotonBase from '@/shared/components/BotonBase.vue'
import { formatearPEN } from '@/modules/tarifas/utils/tarifas'
import { fechaEtiqueta, horaEtiqueta } from '@/modules/calendario/utils/fechas'
import { reservasApi } from '../services/reservas'

const codigo = ref('')
const tipo = ref('codigo')
const resultado = ref(null)
const mensaje = ref('')
const cargando = ref(false)
const camaraActiva = ref(false)
const video = ref(null)
let stream = null
let temporizador = null
let desmontado = false
let iniciando = false

function detenerCamara() {
  camaraActiva.value = false
  if (temporizador) clearTimeout(temporizador)
  temporizador = null
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
}
onBeforeUnmount(() => { desmontado = true; detenerCamara() })

function errorCamara(error) {
  const mensajes = {
    NotAllowedError: 'Permite el acceso a la cámara en el navegador o ingresa el código de reserva.',
    NotFoundError: 'No encontramos una cámara disponible. Ingresa el código de reserva.',
    NotReadableError: 'La cámara está ocupada por otra aplicación. Ciérrala e inténtalo otra vez.',
    OverconstrainedError: 'No se pudo usar esa cámara. Cambia de cámara o ingresa el código.',
    SecurityError: 'La cámara requiere una conexión HTTPS o localhost. Ingresa el código de reserva.',
    NotSupportedError: 'Este navegador no puede leer códigos QR. Ingresa el código de reserva.',
  }
  return mensajes[error?.name] || 'No se pudo abrir o leer la cámara. Ingresa el código de reserva.'
}

async function iniciarCamara() {
  if (iniciando) return
  mensaje.value = ''
  if (!window.isSecureContext) {
    mensaje.value = errorCamara({ name: 'SecurityError' })
    return
  }
  if (!globalThis.BarcodeDetector || !navigator.mediaDevices?.getUserMedia) {
    mensaje.value = 'La cámara no está disponible en este navegador. Ingresa el código de reserva.'
    return
  }
  iniciando = true
  try {
    const Detector = globalThis.BarcodeDetector
    const formatos = await Detector.getSupportedFormats?.()
    if (formatos && !formatos.includes('qr_code')) {
      mensaje.value = errorCamara({ name: 'NotSupportedError' })
      return
    }
    const detector = new Detector({ formats: ['qr_code'] })
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } }, audio: false,
    })
    if (desmontado) { detenerCamara(); return }
    camaraActiva.value = true
    await new Promise((resolve) => requestAnimationFrame(resolve))
    if (!video.value) { detenerCamara(); return }
    video.value.srcObject = stream
    await video.value.play()
    const escanear = async () => {
      if (!camaraActiva.value) return
      try {
        const encontrados = await detector.detect(video.value)
        if (encontrados[0]?.rawValue) {
          codigo.value = encontrados[0].rawValue
          tipo.value = 'qr'
          detenerCamara()
          await consultar()
          return
        }
      } catch (error) {
        detenerCamara()
        if (!desmontado) mensaje.value = errorCamara(error)
        return
      }
      if (camaraActiva.value) temporizador = setTimeout(escanear, 350)
    }
    await escanear()
  } catch (error) {
    detenerCamara()
    if (!desmontado) mensaje.value = errorCamara(error)
  } finally { iniciando = false }
}

async function consultar() {
  if (!codigo.value.trim()) return
  cargando.value = true
  mensaje.value = ''
  resultado.value = null
  try { resultado.value = (await reservasApi.consultarIngreso({ tipo: tipo.value, valor: codigo.value })).data }
  catch { mensaje.value = 'No se pudo validar la reserva. Revisa el código, la sede y el horario.' }
  finally { cargando.value = false }
}
async function registrar() {
  cargando.value = true
  try {
    await reservasApi.registrarIngreso({ tipo: tipo.value, valor: codigo.value })
    resultado.value.asistencia_registrada = true
    mensaje.value = 'Ingreso registrado.'
  } catch (error) {
    if (error.response?.status === 409) {
      resultado.value.asistencia_registrada = true
      mensaje.value = 'El ingreso ya fue registrado.'
    } else mensaje.value = 'No se pudo registrar el ingreso. Inténtalo de nuevo.'
  } finally { cargando.value = false }
}
function editarCodigo() { tipo.value = 'codigo'; resultado.value = null; mensaje.value = '' }
</script>

<template>
  <section class="ingreso" aria-labelledby="ingreso-titulo">
    <div><h3 id="ingreso-titulo">Validar ingreso</h3><p>Escanea el QR o ingresa el código de la reserva.</p></div>
    <form class="ingreso-form" @submit.prevent="consultar">
      <label for="codigo-ingreso">Código de reserva</label>
      <input id="codigo-ingreso" v-model.trim="codigo" maxlength="256" autocomplete="off" placeholder="ATP-XXXXXXXXXXXX" @input="editarCodigo">
      <div class="ingreso-acciones"><BotonBase tipo="submit" variante="primario" :deshabilitado="!codigo || cargando">Consultar</BotonBase>
        <BotonBase v-if="!camaraActiva" tipo="button" @click="iniciarCamara">Abrir cámara</BotonBase>
        <BotonBase v-else tipo="button" @click="detenerCamara">Cerrar cámara</BotonBase></div>
    </form>
    <video v-if="camaraActiva" ref="video" class="ingreso-video" playsinline muted aria-label="Vista previa de la cámara" />
    <p v-if="mensaje" role="status" class="ingreso-mensaje">{{ mensaje }}</p>
    <div v-if="resultado" class="ingreso-resultado">
      <strong>{{ resultado.sede }} · {{ resultado.cancha }}</strong>
      <span>{{ fechaEtiqueta(resultado.inicio.slice(0, 10)) }} · {{ horaEtiqueta(resultado.inicio) }}–{{ horaEtiqueta(resultado.fin) }}</span>
      <span>Saldo pendiente: {{ formatearPEN(resultado.saldo_pendiente, resultado.moneda) }}</span>
      <strong v-if="resultado.asistencia_registrada">Ingreso ya registrado</strong>
      <BotonBase v-else variante="primario" :deshabilitado="cargando" @click="registrar">Registrar ingreso</BotonBase>
    </div>
  </section>
</template>

<style scoped>
.ingreso { display: grid; gap: 14px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--surface); padding: 20px; }
.ingreso h3, .ingreso p { margin: 0; }
.ingreso p { color: var(--text-muted); }
.ingreso-form { display: grid; gap: 8px; }
.ingreso-form label { font-size: 14px; font-weight: 600; }
.ingreso-form input { min-height: 44px; width: 100%; border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--input-bg); color: var(--text); padding: 0 12px; }
.ingreso-acciones { display: flex; flex-wrap: wrap; gap: 8px; }
.ingreso-video { width: min(100%, 420px); border-radius: var(--radius-md); background: var(--brand-charcoal); }
.ingreso-resultado { display: grid; gap: 7px; border-radius: var(--radius-md); background: var(--surface-2); padding: 16px; }
.ingreso-mensaje { border-left: 3px solid var(--brand-lime); padding-left: 10px; }
</style>
