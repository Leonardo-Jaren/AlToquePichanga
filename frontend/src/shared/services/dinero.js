export function formatearDinero(monto, moneda = 'PEN', locale = 'es-PE') {
  const texto = String(monto ?? '0').trim().replace(',', '.')
  const coincidencia = texto.match(/^(-?)(\d+)(?:\.(\d+))?$/)
  if (!coincidencia) return `${moneda} ${texto}`

  const [, signo, entero, decimal = ''] = coincidencia
  let formato
  try {
    formato = new Intl.NumberFormat(locale, { style: 'currency', currency: moneda })
  } catch {
    return `${moneda} ${texto}`
  }
  const decimales = formato.resolvedOptions().maximumFractionDigits
  const fraccion = decimal.padEnd(decimales, '0').slice(0, decimales)
  const agrupado = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(BigInt(entero))
  return formato.formatToParts(signo ? -0 : 0).map((parte) => {
    if (parte.type === 'integer') return agrupado
    if (parte.type === 'fraction') return fraccion
    if (parte.type === 'minusSign') return signo ? parte.value : ''
    if (parte.type === 'decimal' && decimales === 0) return ''
    return parte.value
  }).join('')
}
