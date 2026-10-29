export function calcularAdelantoMinimo(total) {
  const coincidencia = String(total ?? '').match(/^(\d+)(?:\.(\d{1,2}))?$/)
  if (!coincidencia) return null
  const centavos = BigInt(coincidencia[1]) * 100n + BigInt((coincidencia[2] || '').padEnd(2, '0'))
  const adelanto = (centavos + 1n) / 2n
  return `${adelanto / 100n}.${String(adelanto % 100n).padStart(2, '0')}`
}

export function etiquetaEstadoReserva(estado) {
  return ({
    retenida: 'Retenida temporalmente',
    pendiente_pago: 'Pendiente de pago',
    pendiente_verificacion: 'Pendiente de verificación',
    confirmada: 'Confirmada',
    vencida: 'Vencida',
    cancelada: 'Cancelada',
    rechazada: 'Rechazada',
    finalizada: 'Finalizada',
  })[estado] || 'Estado por revisar'
}

export function segundosRestantes(fechaVencimiento, ahora = Date.now()) {
  const fecha = Date.parse(fechaVencimiento)
  return Number.isFinite(fecha) ? Math.max(0, Math.ceil((fecha - ahora) / 1000)) : 0
}

export function formatoCuentaRegresiva(segundos) {
  const horas = Math.floor(segundos / 3600)
  const minutos = Math.floor((segundos % 3600) / 60)
  const restantes = segundos % 60
  return [horas, minutos, restantes].map((parte) => String(parte).padStart(2, '0')).join(':')
}
