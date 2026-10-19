const tiposPorExtension = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
}

export function errorImagenCancha(archivo) {
  if (!archivo) return ''
  if (archivo.size > 5 * 1024 * 1024) return 'La imagen no puede superar 5 MB.'
  const extension = archivo.name.slice(archivo.name.lastIndexOf('.')).toLowerCase()
  const tipoEsperado = tiposPorExtension[extension]
  if (!tipoEsperado) return 'Elige una imagen PNG, JPG o WebP válida.'
  if (archivo.type && archivo.type !== tipoEsperado) return 'El tipo de imagen no coincide con su extensión.'
  return ''
}
