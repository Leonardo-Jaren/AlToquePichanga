"""Publicación de cambios mínimos de disponibilidad después del commit."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from asgiref.sync import async_to_sync
from channels.exceptions import ChannelFull
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

MOTIVOS = {
    "retencion_creada",
    "retencion_cancelada",
    "retencion_vencida",
    "retencion_pago_extendida",
    "horario_actualizado",
    "excepcion_actualizada",
    "tarifa_actualizada",
    "cancha_actualizada",
    "sede_actualizada",
}


def grupo_disponibilidad(cancha_id: int, fecha: date | str | None = None) -> str:
    if isinstance(fecha, str):
        fecha = date.fromisoformat(fecha)
    sufijo = fecha.strftime("%Y%m%d") if isinstance(fecha, (date, datetime)) else "general"
    return f"disponibilidad-cancha.{cancha_id}.{sufijo}"


def programar_cambio_disponibilidad(
    cancha_id: int, fecha: date | None, motivo: str
) -> None:
    """Registra un único aviso sin datos privados y lo envía al confirmar la transacción."""
    if motivo not in MOTIVOS:
        raise ValueError("Motivo de disponibilidad no permitido.")
    evento = {
        "tipo": "disponibilidad_actualizada",
        "cancha_id": int(cancha_id),
        "fecha": fecha.isoformat() if fecha else None,
        "motivo": motivo,
    }
    transaction.on_commit(lambda: _publicar(evento), robust=True)


def programar_cambio_sede(sede_id: int, motivo: str) -> None:
    from apps.canchas.models import Cancha

    for cancha_id in Cancha.objects.filter(sede_id=sede_id).values_list("pk", flat=True):
        programar_cambio_disponibilidad(cancha_id, None, motivo)


def fechas_en_intervalo(inicio, fin) -> list[date]:
    primera = timezone.localtime(inicio).date()
    ultima = timezone.localtime(fin - timedelta(microseconds=1)).date()
    return [primera + timedelta(days=dias) for dias in range((ultima - primera).days + 1)]


def programar_cambio_intervalo(cancha_id: int, inicio, fin, motivo: str) -> None:
    for fecha in fechas_en_intervalo(inicio, fin):
        programar_cambio_disponibilidad(cancha_id, fecha, motivo)


def programar_cambio_sede_intervalo(
    sede_id: int, inicio, fin, motivo: str, cancha_id: int | None = None
) -> None:
    from apps.canchas.models import Cancha

    ids = [cancha_id] if cancha_id is not None else Cancha.objects.filter(
        sede_id=sede_id
    ).values_list("pk", flat=True)
    for identificador in ids:
        programar_cambio_intervalo(identificador, inicio, fin, motivo)


def _publicar(evento: dict) -> None:
    """Un error temporal del transporte no invalida la mutación ya confirmada."""
    try:
        capa = get_channel_layer()
        if capa is None:
            return
        async_to_sync(capa.group_send)(
            grupo_disponibilidad(evento["cancha_id"], evento["fecha"]),
            {"type": "disponibilidad.actualizada", "evento": evento},
        )
    except (ChannelFull, OSError, RedisError, TimeoutError):
        logger.warning(
            "No se pudo publicar un cambio de disponibilidad (cancha=%s).",
            evento["cancha_id"],
        )
