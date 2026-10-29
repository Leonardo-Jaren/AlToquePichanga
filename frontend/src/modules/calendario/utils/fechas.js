export function fechaActualLima() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date())
}

export function desplazarFecha(fecha, dias) {
  const fechaUTC = new Date(`${fecha}T12:00:00Z`)
  fechaUTC.setUTCDate(fechaUTC.getUTCDate() + dias)
  return fechaUTC.toISOString().slice(0, 10)
}

export function inicioSemana(fecha) {
  const fechaUTC = new Date(`${fecha}T12:00:00Z`)
  const dia = (fechaUTC.getUTCDay() + 6) % 7
  fechaUTC.setUTCDate(fechaUTC.getUTCDate() - dia)
  return fechaUTC.toISOString().slice(0, 10)
}

export function rangoCalendario(vista, fecha) {
  if (vista === 'dia') return { desde: fecha, hasta: fecha }
  const desde = inicioSemana(fecha)
  return { desde, hasta: desplazarFecha(desde, 6) }
}

export function diasEntre(desde, hasta) {
  const resultado = []
  for (let fecha = desde; fecha <= hasta; fecha = desplazarFecha(fecha, 1)) {
    resultado.push(fecha)
  }
  return resultado
}

export function fechaEtiqueta(fecha, opciones = {}) {
  const [anio, mes, dia] = fecha.split('-').map(Number)
  return new Intl.DateTimeFormat('es-PE', {
    timeZone: 'UTC', weekday: opciones.completa ? 'long' : 'short',
    day: 'numeric', month: opciones.completa ? 'long' : 'short',
  }).format(new Date(Date.UTC(anio, mes - 1, dia, 12)))
}

export function horaEtiqueta(valor, zonaHoraria = 'America/Lima') {
  return new Intl.DateTimeFormat('es-PE', {
    timeZone: zonaHoraria, hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(valor))
}

export function horaLocalISO(valor) {
  return String(valor || '').slice(11, 16)
}
