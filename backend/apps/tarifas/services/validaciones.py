from datetime import date, time, timedelta

from rest_framework.exceptions import ValidationError

from apps.tarifas.models import ReglaTarifa, TipoTarifa

PRIORIDAD_TARIFA = {
    TipoTarifa.DIURNA: 1,
    TipoTarifa.NOCTURNA: 1,
    TipoTarifa.FIN_SEMANA: 2,
    TipoTarifa.FERIADO: 3,
    TipoTarifa.ESPECIAL: 4,
}


def _rango_efectivo(regla: ReglaTarifa) -> tuple[date, date]:
    inicio = regla.vigente_desde
    fin = regla.vigente_hasta or date.max
    if regla.tipo in (TipoTarifa.FERIADO, TipoTarifa.ESPECIAL):
        inicio = max(inicio, regla.fecha_aplicable_desde)
        fin = min(fin, regla.fecha_aplicable_hasta)
    return inicio, fin


def _desplazar(fecha: date, dias: int) -> date:
    try:
        return fecha + timedelta(days=dias)
    except OverflowError:
        return date.min if dias < 0 else date.max


def _fechas_muestra(inicio: date, fin: date) -> set[date]:
    if fin == date.max:
        fin = _desplazar(inicio, 14)
    if (fin - inicio).days <= 28:
        return {
            _desplazar(inicio, dia)
            for dia in range(-1, (fin - inicio).days + 2)
        }
    fechas = set()
    for base in (inicio, fin):
        fechas.update(_desplazar(base, dia) for dia in range(-14, 16))
    return fechas


def _minutos(hora: time) -> int:
    return hora.hour * 60 + hora.minute


def _aplica_en_fecha(regla: ReglaTarifa, fecha: date) -> bool:
    if fecha < regla.vigente_desde or (regla.vigente_hasta and fecha > regla.vigente_hasta):
        return False
    if regla.tipo in (TipoTarifa.DIURNA, TipoTarifa.NOCTURNA):
        return fecha.weekday() in (regla.dias_semana or [])
    if regla.tipo == TipoTarifa.FIN_SEMANA:
        return fecha.weekday() >= 5
    return regla.fecha_aplicable_desde <= fecha <= regla.fecha_aplicable_hasta


def _intervalo_regla(regla: ReglaTarifa, fecha: date) -> tuple[int, int]:
    inicio = _minutos(regla.hora_inicio) if not regla.todo_el_dia else 0
    fin = _minutos(regla.hora_fin) if not regla.todo_el_dia else 1440
    if not regla.todo_el_dia and fin < inicio:
        fin += 1440
    base = fecha.toordinal() * 1440
    return base + inicio, base + fin


def _solapan_reglas(a: ReglaTarifa, b: ReglaTarifa) -> bool:
    if PRIORIDAD_TARIFA[a.tipo] != PRIORIDAD_TARIFA[b.tipo]:
        return False
    inicio_a, fin_a = _rango_efectivo(a)
    inicio_b, fin_b = _rango_efectivo(b)
    if fin_a < _desplazar(inicio_b, -1) or fin_b < _desplazar(inicio_a, -1):
        return False

    fechas = set()
    for limite in (inicio_a, fin_a, inicio_b, fin_b):
        if limite != date.max:
            fechas.update(_desplazar(limite, delta) for delta in range(-2, 3))
    inicio, fin = max(inicio_a, inicio_b), min(fin_a, fin_b)
    if inicio <= fin:
        fechas.update(_fechas_muestra(inicio, fin))

    intervalos_a = [
        _intervalo_regla(a, fecha) for fecha in fechas if _aplica_en_fecha(a, fecha)
    ]
    intervalos_b = [
        _intervalo_regla(b, fecha) for fecha in fechas if _aplica_en_fecha(b, fecha)
    ]
    for intervalo_a in intervalos_a:
        for intervalo_b in intervalos_b:
            if intervalo_a[0] < intervalo_b[1] and intervalo_a[1] > intervalo_b[0]:
                return True
    return False


def validar_regla_sin_ambiguedad(
    regla: ReglaTarifa, existentes: list[ReglaTarifa]
) -> None:
    if not regla.activa:
        return
    for existente in existentes:
        if existente.pk == regla.pk or not existente.activa:
            continue
        if _solapan_reglas(regla, existente):
            raise ValidationError({
                "non_field_errors": [
                    "Esta tarifa se cruza con otra regla del mismo nivel. Ajusta sus días, "
                    "horarios o vigencia para evitar precios ambiguos."
                ]
            })
