export const DIAS_SEMANA = [
  { id: 0, nombre: 'Lunes', corto: 'Lun' },
  { id: 1, nombre: 'Martes', corto: 'Mar' },
  { id: 2, nombre: 'Miércoles', corto: 'Mié' },
  { id: 3, nombre: 'Jueves', corto: 'Jue' },
  { id: 4, nombre: 'Viernes', corto: 'Vie' },
  { id: 5, nombre: 'Sábado', corto: 'Sáb' },
  { id: 6, nombre: 'Domingo', corto: 'Dom' },
]

export function validarIntervalos(intervalos) {
  const porDia = Array.from({ length: 7 }, () => [])
  for (const intervalo of intervalos) {
    const inicio = minutos(intervalo.hora_apertura)
    const fin = minutos(intervalo.hora_cierre)
    if (!Number.isInteger(intervalo.dia_semana) || intervalo.dia_semana < 0 || intervalo.dia_semana > 6) return 'Selecciona un día válido.'
    if (inicio === null || fin === null || inicio === fin) return 'Cada intervalo necesita horas válidas y distintas.'
    const diaSiguiente = (intervalo.dia_semana + 1) % 7
    if (fin > inicio) porDia[intervalo.dia_semana].push([inicio, fin])
    else {
      porDia[intervalo.dia_semana].push([inicio, 1440])
      if (diaSiguiente !== intervalo.dia_semana) porDia[diaSiguiente].push([0, fin])
    }
  }
  for (const periodos of porDia) {
    periodos.sort((a, b) => a[0] - b[0])
    if (periodos.some((periodo, indice) => indice > 0 && periodo[0] < periodos[indice - 1][1])) {
      return 'Los intervalos del mismo día no pueden superponerse.'
    }
  }
  return ''
}

export function validarIntervalosDentroDeMarco(intervalos, marco) {
  const propio = fragmentos(intervalos)
  const sede = fragmentos(marco)
  for (let dia = 0; dia < 7; dia += 1) {
    const marcosDia = sede.filter((item) => item.dia === dia).sort((a, b) => a.inicio - b.inicio)
    for (const tramo of propio.filter((item) => item.dia === dia)) {
      let cubiertoHasta = tramo.inicio
      for (const limite of marcosDia) {
        if (limite.inicio > cubiertoHasta) break
        if (limite.fin > cubiertoHasta) cubiertoHasta = limite.fin
        if (cubiertoHasta >= tramo.fin) break
      }
      if (cubiertoHasta < tramo.fin) return 'El horario propio debe quedar dentro del horario de sede de cada día.'
    }
  }
  return ''
}

function minutos(hora) {
  if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(hora || '')) return null
  const [h, m] = hora.split(':').map(Number)
  return h * 60 + m
}

function fragmentos(intervalos) {
  const resultado = []
  for (const item of intervalos) {
    const inicio = minutos(item.hora_apertura)
    const fin = minutos(item.hora_cierre)
    if (inicio === null || fin === null || inicio === fin) continue
    const dia = Number(item.dia_semana)
    if (fin > inicio) resultado.push({ dia, inicio, fin })
    else {
      resultado.push({ dia, inicio, fin: 1440 })
      if (fin > 0) resultado.push({ dia: (dia + 1) % 7, inicio: 0, fin })
    }
  }
  return resultado
}

export function normalizarIntervalos(intervalos = []) {
  return intervalos.map((item) => ({
    dia_semana: Number(item.dia_semana),
    hora_apertura: String(item.hora_apertura || '').slice(0, 5),
    hora_cierre: String(item.hora_cierre || '').slice(0, 5),
  })).sort((a, b) => a.dia_semana - b.dia_semana || a.hora_apertura.localeCompare(b.hora_apertura))
}

export function fechaHoraLima(fecha, hora) {
  return `${fecha}T${hora}:00-05:00`
}

export function diasEntre(desde, hasta) {
  const inicio = Date.parse(`${desde}T00:00:00Z`)
  const fin = Date.parse(`${hasta}T00:00:00Z`)
  return Number.isFinite(inicio) && Number.isFinite(fin) ? Math.round((fin - inicio) / 86400000) : -1
}
