const estados = {
  pendiente_pago: 'Pendiente de pago',
  pendiente_revision: 'Comprobante por revisar',
  aprobado: 'Pago revisado',
  rechazado: 'Comprobante rechazado',
  vencido: 'Plazo vencido',
  pago_tardio: 'Declarado fuera de plazo',
}

export function etiquetaEstadoPago(estado) {
  return estados[estado] || estado || 'Sin estado'
}

export function soles(valor) {
  return new Intl.NumberFormat('es-PE', {
    style: 'currency', currency: 'PEN', minimumFractionDigits: 2,
  }).format(Number(valor || 0))
}

export function fechaPago(valor) {
  if (!valor) return '—'
  return new Intl.DateTimeFormat('es-PE', {
    dateStyle: 'medium', timeStyle: 'short', timeZone: 'America/Lima', hourCycle: 'h23',
  }).format(new Date(valor))
}
