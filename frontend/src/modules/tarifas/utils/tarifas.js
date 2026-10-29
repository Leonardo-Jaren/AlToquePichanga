export const TIPOS_TARIFA = [
  { value: 'diurna', label: 'Diurna' },
  { value: 'nocturna', label: 'Nocturna' },
  { value: 'fin_semana', label: 'Fin de semana' },
  { value: 'feriado', label: 'Feriado' },
  { value: 'especial', label: 'Fecha especial' },
]

export const DIAS_SEMANA = [
  { value: 0, label: 'Lunes' }, { value: 1, label: 'Martes' },
  { value: 2, label: 'Miércoles' }, { value: 3, label: 'Jueves' },
  { value: 4, label: 'Viernes' }, { value: 5, label: 'Sábado' },
  { value: 6, label: 'Domingo' },
]

export function fechaActualLima() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Lima', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date())
}

export function desplazarFecha(fecha, dias) {
  const base = new Date(`${fecha}T12:00:00Z`)
  base.setUTCDate(base.getUTCDate() + dias)
  return base.toISOString().slice(0, 10)
}

export function formatearPEN(valor, moneda = 'PEN') {
  const partes = String(valor ?? '').match(/^(-?)(\d+)(?:\.(\d{1,2}))?$/)
  if (!partes) return 'Sin precio'
  const [, signo, enteros, decimales = ''] = partes
  const agrupado = new Intl.NumberFormat('es-PE', { useGrouping: true }).format(BigInt(enteros))
  const monto = `${signo}${agrupado}.${decimales.padEnd(2, '0')}`
  return moneda === 'PEN' ? `S/ ${monto}` : `${moneda} ${monto}`
}

export function fechaEtiqueta(fecha) {
  if (!fecha) return ''
  const [year, month, day] = fecha.split('-').map(Number)
  return new Intl.DateTimeFormat('es-PE', {
    timeZone: 'America/Lima', weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  }).format(new Date(Date.UTC(year, month - 1, day, 12)))
}

export function horaEtiqueta(valor) {
  if (!valor) return ''
  return new Intl.DateTimeFormat('es-PE', {
    timeZone: 'America/Lima', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).format(new Date(valor))
}

export function mensajeErrorApi(fallo, predeterminado) {
  const datos = fallo?.response?.data || {}
  if (typeof datos.detail === 'string') return datos.detail
  const mensajes = Object.values(datos).flat().filter((valor) => typeof valor === 'string')
  return mensajes[0] || predeterminado
}
