from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.utils import timezone

from apps.horarios.services.disponibilidad import (
    construir_disponibilidad_operativa,
    consultar_disponibilidad_operativa,
    consultar_disponibilidad_operativa_publica,
)
from apps.tarifas.repositories.tarifas import cancha_tarifaria, reglas_de_cancha
from apps.tarifas.services.calculo import (
    ZONA_HORARIA,
    calcular_precio,
    seleccionar_regla,
)


def _bloques_por_inicio(bloques: list[dict]) -> dict[tuple[date, time], dict]:
    resultado = {}
    for bloque in bloques:
        inicio = timezone.localtime(
            datetime.fromisoformat(bloque["fecha_inicio"]), ZONA_HORARIA
        )
        resultado[(inicio.date(), inicio.time().replace(tzinfo=None))] = bloque
    return resultado


def consultar_disponibilidad_tarifada(
    usuario: User, cancha_id: int, desde: date, hasta: date
) -> dict:
    resultado = consultar_disponibilidad_operativa(usuario, cancha_id, desde, hasta)
    cancha = cancha_tarifaria(usuario, cancha_id)
    return agregar_precios_a_disponibilidad(resultado, cancha)


def consultar_disponibilidad_tarifada_publica(
    cancha, desde: date, hasta: date
) -> dict:
    resultado = consultar_disponibilidad_operativa_publica(cancha, desde, hasta)
    motivos_publicos = {
        "cerrada": "Cierre temporal.",
        "mantenimiento": "La cancha está en mantenimiento.",
        "pasada": "El bloque ya comenzó.",
        "cancha_inactiva": "La cancha está inactiva.",
        "sede_inactiva": "La sede está inactiva.",
    }
    for bloque in resultado["bloques"]:
        if bloque["estado"] in motivos_publicos:
            bloque["motivo"] = motivos_publicos[bloque["estado"]]
    return agregar_precios_a_disponibilidad(resultado, cancha)


def agregar_precios_a_disponibilidad(resultado: dict, cancha) -> dict:
    reglas = list(reglas_de_cancha(cancha, solo_activas=True))
    bloques = []
    for bloque in resultado["bloques"]:
        item = dict(bloque)
        if not item["habilitada_operativamente"]:
            item.update({"precio": None, "tipo_tarifa": None, "moneda": None,
                         "tarifa_estado": "no_disponible"})
        else:
            inicio = timezone.localtime(
                datetime.fromisoformat(item["fecha_inicio"]), ZONA_HORARIA
            )
            regla = seleccionar_regla(reglas, inicio.date(), inicio.time())
            if regla is None:
                item.update({"precio": None, "tipo_tarifa": None, "moneda": None,
                             "tarifa_estado": "sin_configurar"})
            else:
                item.update({
                    "precio": f"{regla.precio_hora:.2f}",
                    "tipo_tarifa": regla.tipo,
                    "moneda": regla.moneda,
                    "tarifa_estado": "configurada",
                })
        bloques.append(item)
    resultado["bloques"] = bloques
    return resultado


def previsualizar_precio(
    usuario: User, cancha_id: int, fecha: date, hora_inicio: time, duracion_horas: int
) -> dict:
    cancha = cancha_tarifaria(usuario, cancha_id)
    return previsualizar_precio_para_cancha(cancha, fecha, hora_inicio, duracion_horas)


def previsualizar_precio_para_cancha(
    cancha, fecha: date, hora_inicio: time, duracion_horas: int
) -> dict:
    minutos_fin = hora_inicio.hour * 60 + hora_inicio.minute + duracion_horas * 60 - 1
    fin = fecha + timedelta(days=minutos_fin // 1440)
    operacion = construir_disponibilidad_operativa(cancha, fecha, fin)
    bloques = _bloques_por_inicio(operacion["bloques"])
    reglas = list(reglas_de_cancha(cancha, solo_activas=True))
    return calcular_precio(
        cancha.sede.empresa, cancha, fecha, hora_inicio, duracion_horas, bloques, reglas
    )
