export function bloquePuedeCotizar(bloque) {
  return Boolean(bloque?.habilitada_operativamente
    && bloque.reservable !== false
    && bloque.tarifa_estado === 'configurada'
    && typeof bloque.precio === 'string'
    && bloque.precio.length)
}

export function etiquetaEstadoBloque(bloque) {
  if (bloque?.estado === 'retenida') return 'Retenida temporalmente'
  if (bloque?.estado === 'ocupada') return 'Horario reservado'
  if (bloque?.estado === 'mantenimiento') return 'En mantenimiento'
  if (bloque?.estado === 'cerrada') return 'Cerrado'
  if (bloque?.estado === 'pasada') return 'Horario pasado'
  if (bloque?.estado === 'cancha_inactiva') return 'Cancha inactiva'
  if (bloque?.estado === 'sede_inactiva') return 'Sede inactiva'
  if (bloque?.habilitada_operativamente && bloque?.tarifa_estado === 'sin_configurar') {
    return 'Tarifa no configurada'
  }
  return bloquePuedeCotizar(bloque) ? 'Con tarifa' : 'No habilitado'
}

export function claseEstadoBloque(bloque) {
  if (bloquePuedeCotizar(bloque)) return 'success'
  if (['retenida', 'ocupada'].includes(bloque?.estado)) return 'warning'
  if (bloque?.habilitada_operativamente) return 'warning'
  return 'muted'
}
