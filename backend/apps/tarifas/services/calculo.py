from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.canchas.models import Cancha
from apps.empresas.models import Empresa
from apps.tarifas.models import ReglaTarifa, TipoTarifa
from apps.tarifas.services.validaciones import PRIORIDAD_TARIFA

CENTAVO = Decimal("0.01")
ZONA_HORARIA = ZoneInfo(settings.TIME_ZONE)


def _hora_aplicable(regla: ReglaTarifa, fecha: date, hora: time) -> date | None:
    if regla.todo_el_dia:
        return fecha
    inicio, fin = regla.hora_inicio, regla.hora_fin
    if inicio < fin:
        return fecha if inicio <= hora < fin else None
    if hora >= inicio:
        return fecha
    if hora < fin:
        return fecha - timedelta(days=1)
    return None


def _regla_aplica_en_fecha(regla: ReglaTarifa, fecha: date) -> bool:
    if fecha < regla.vigente_desde or (regla.vigente_hasta and fecha > regla.vigente_hasta):
        return False
    if regla.tipo in (TipoTarifa.DIURNA, TipoTarifa.NOCTURNA):
        return fecha.weekday() in (regla.dias_semana or [])
    if regla.tipo == TipoTarifa.FIN_SEMANA:
        return fecha.weekday() >= 5
    return regla.fecha_aplicable_desde <= fecha <= regla.fecha_aplicable_hasta


def seleccionar_regla(
    reglas: list[ReglaTarifa], fecha: date, hora: time
) -> ReglaTarifa | None:
    aplicables = []
    for regla in reglas:
        fecha_regla = _hora_aplicable(regla, fecha, hora)
        if fecha_regla and _regla_aplica_en_fecha(regla, fecha_regla):
            aplicables.append(regla)
    if not aplicables:
        return None
    prioridad = max(PRIORIDAD_TARIFA[regla.tipo] for regla in aplicables)
    ganadoras = [regla for regla in aplicables if PRIORIDAD_TARIFA[regla.tipo] == prioridad]
    if len(ganadoras) != 1:
        raise ValidationError({
            "tarifa": "Hay más de una tarifa activa para este bloque. Ajusta las reglas de la cancha."
        })
    return ganadoras[0]


def calcular_precio(
    empresa: Empresa,
    cancha: Cancha,
    fecha: date,
    hora_inicio: time,
    duracion_horas: int,
    bloques_operativos: dict[tuple[date, time], dict],
    reglas: list[ReglaTarifa],
) -> dict:
    """Calcula un total sobre bloques operativos ya comprobados, sin crear una reserva."""
    if cancha.sede.empresa_id != empresa.pk:
        raise PermissionDenied("La cancha no pertenece a la empresa indicada.")
    if not 1 <= duracion_horas <= 24:
        raise ValidationError({"duracion_horas": "La duración debe estar entre 1 y 24 horas."})

    inicio = timezone.make_aware(datetime.combine(fecha, hora_inicio), ZONA_HORARIA)
    bloques = []
    total = Decimal("0.00")
    for indice in range(duracion_horas):
        inicio_bloque = timezone.localtime(inicio + timedelta(hours=indice), ZONA_HORARIA)
        clave = (inicio_bloque.date(), inicio_bloque.time().replace(tzinfo=None))
        disponible = bloques_operativos.get(clave)
        if not disponible:
            raise ValidationError({
                "hora_inicio": "El horario solicitado no coincide con bloques operativos de una hora."
            })
        if not disponible.get("habilitada_operativamente"):
            motivo = disponible.get("motivo") or "El bloque está cerrado."
            raise ValidationError({"horario": f"{inicio_bloque:%d/%m %H:%M}: {motivo}"})
        regla = seleccionar_regla(reglas, inicio_bloque.date(), inicio_bloque.time())
        if regla is None:
            raise ValidationError({
                "tarifa": f"No hay un precio configurado para {inicio_bloque:%d/%m %H:%M}. "
                "Configura una tarifa para cada bloque antes de calcular el total."
            })
        precio = Decimal(regla.precio_hora).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        total += precio
        fin_bloque = inicio_bloque + timedelta(hours=1)
        bloques.append({
            "fecha_inicio": inicio_bloque.isoformat(),
            "fecha_fin": fin_bloque.isoformat(),
            "tipo_tarifa": regla.tipo,
            "nombre_tarifa": regla.nombre or regla.get_tipo_display(),
            "precio_hora": f"{precio:.2f}",
            "precio": f"{precio:.2f}",
            "moneda": regla.moneda,
        })

    total = total.quantize(CENTAVO, rounding=ROUND_HALF_UP)
    fin = inicio + timedelta(hours=duracion_horas)
    return {
        "empresa_id": empresa.pk,
        "cancha_id": cancha.pk,
        "fecha": fecha.isoformat(),
        "hora_inicio": inicio.isoformat(),
        "hora_fin": fin.isoformat(),
        "duracion_horas": duracion_horas,
        "bloques": bloques,
        "subtotal": f"{total:.2f}",
        "total": f"{total:.2f}",
        "moneda": "PEN",
    }
