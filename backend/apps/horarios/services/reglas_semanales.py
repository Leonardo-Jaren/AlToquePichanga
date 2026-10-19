from collections.abc import Iterable
from datetime import time

from rest_framework.exceptions import ValidationError

MINUTOS_SEMANA = 7 * 24 * 60


def _minutos(hora: time) -> int:
    if isinstance(hora, str):
        hora = time.fromisoformat(hora)
    return hora.hour * 60 + hora.minute


def _rango_semanal(intervalo: dict) -> tuple[int, int]:
    inicio = intervalo["dia_semana"] * 1440 + _minutos(intervalo["hora_apertura"])
    cierre = intervalo["dia_semana"] * 1440 + _minutos(intervalo["hora_cierre"])
    if cierre <= inicio:
        cierre += 1440
    return inicio, cierre


def validar_intervalos(intervalos: Iterable[dict]) -> list[dict]:
    normalizados = list(intervalos)
    for intervalo in normalizados:
        if intervalo["hora_apertura"] == intervalo["hora_cierre"]:
            raise ValidationError({"intervalos": "La apertura y el cierre deben ser distintos."})

    rangos = [(_rango_semanal(item), indice) for indice, item in enumerate(normalizados)]
    for indice, ((inicio, fin), _) in enumerate(rangos):
        for otro_indice, ((otro_inicio, otro_fin), _) in enumerate(rangos):
            if indice >= otro_indice:
                continue
            for desplazamiento in (-MINUTOS_SEMANA, 0, MINUTOS_SEMANA):
                if max(inicio, otro_inicio + desplazamiento) < min(fin, otro_fin + desplazamiento):
                    raise ValidationError({
                        "intervalos": "Los intervalos semanales no pueden superponerse, incluso al cruzar medianoche."
                    })
    return sorted(
        normalizados,
        key=lambda item: (item["dia_semana"], item["hora_apertura"]),
    )


def intervalos_contenidos(intervalos_hijo: list[dict], intervalos_padre: list[dict]) -> bool:
    """Comprueba la contención de intervalos semanales en el ciclo de siete días."""
    padres = [_rango_semanal(item) for item in intervalos_padre]
    for hijo in intervalos_hijo:
        inicio, fin = _rango_semanal(hijo)
        coberturas = sorted(
            (padre_inicio + desplazamiento, padre_fin + desplazamiento)
            for padre_inicio, padre_fin in padres
            for desplazamiento in (-MINUTOS_SEMANA, 0, MINUTOS_SEMANA)
            if padre_inicio + desplazamiento < fin and padre_fin + desplazamiento > inicio
        )
        cursor = inicio
        for cobertura_inicio, cobertura_fin in coberturas:
            if cobertura_inicio > cursor:
                break
            cursor = max(cursor, cobertura_fin)
            if cursor >= fin:
                break
        if cursor < fin:
            return False
    return True
