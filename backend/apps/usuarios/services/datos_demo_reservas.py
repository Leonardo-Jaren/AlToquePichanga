"""Retenciones locales reproducibles y trazables para probar la Fase 4A."""

from __future__ import annotations

from datetime import date, time, timedelta
from uuid import NAMESPACE_URL, uuid5

from django.core.management.base import CommandError
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.canchas.models import Cancha
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.estados import cambiar_estado
from apps.reservas.services.reservas import HorarioNoDisponible, crear_retencion
from apps.usuarios.services.datos_demo import identidad_demo


def _proximo_lunes() -> date:
    hoy = timezone.localdate()
    dias = (0 - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=dias)


def _clave_reserva(clave: str, fecha: date):
    return uuid5(NAMESPACE_URL, identidad_demo(f"reserva:{clave}:{fecha.isoformat()}"))


def _vencer_solo_reserva_demo(reserva: Reserva) -> None:
    reserva = Reserva.objects.select_for_update().get(pk=reserva.pk)
    if reserva.estado == EstadoReserva.VENCIDA:
        return
    estados_vigentes = {
        EstadoReserva.RETENIDA, EstadoReserva.PENDIENTE_PAGO,
        EstadoReserva.PENDIENTE_VERIFICACION, EstadoReserva.PENDIENTE_CONFIRMACION,
    }
    if reserva.estado not in estados_vigentes:
        raise CommandError("Una reserva demo tiene un estado inesperado; no se modificó.")
    ahora = timezone.now()
    reserva.retencion_vence_en = ahora - timedelta(seconds=1)
    campos = ["retencion_vence_en", "actualizada_en"]
    if reserva.revision_pago_vence_en:
        reserva.revision_pago_vence_en = ahora - timedelta(seconds=1)
        campos.append("revision_pago_vence_en")
    reserva.save(update_fields=campos)
    cambiar_estado(reserva, EstadoReserva.VENCIDA, "Retención vencida del fixture local.")
    reserva.bloques.filter(liberado_en__isnull=True).update(liberado_en=ahora)
    from apps.pagos.services.pagos import cerrar_pagos_vencidos

    cerrar_pagos_vencidos(reserva, ahora)


def _crear_reserva_demo(
    jugador, cancha: Cancha, fecha: date, hora: time, duracion: int, clave: str,
    *, vencida: bool = False,
) -> Reserva:
    try:
        reserva, _ = crear_retencion(
            jugador, cancha.pk, fecha, hora, duracion, _clave_reserva(clave, fecha)
        )
    except HorarioNoDisponible as exc:
        raise CommandError(
            f"No se pudo reservar el horario de demostración {clave}; ya está ocupado."
        ) from exc
    except ValidationError as exc:
        raise CommandError(
            f"No se pudo crear la reserva de demostración {clave}; revisa horarios y tarifas."
        ) from exc

    if vencida:
        _vencer_solo_reserva_demo(reserva)
    elif reserva.estado in {
        EstadoReserva.RETENIDA, EstadoReserva.PENDIENTE_PAGO,
        EstadoReserva.PENDIENTE_VERIFICACION, EstadoReserva.PENDIENTE_CONFIRMACION,
    } and (reserva.revision_pago_vence_en or reserva.retencion_vence_en) <= timezone.now():
        _vencer_solo_reserva_demo(reserva)
    elif reserva.estado not in {
        EstadoReserva.RETENIDA, EstadoReserva.PENDIENTE_PAGO,
        EstadoReserva.PENDIENTE_VERIFICACION, EstadoReserva.PENDIENTE_CONFIRMACION,
        EstadoReserva.CONFIRMADA, EstadoReserva.VENCIDA, EstadoReserva.CANCELADA,
        EstadoReserva.RECHAZADA, EstadoReserva.FINALIZADA,
    }:
        raise CommandError("Una reserva demo tiene un estado inesperado; no se modificó.")
    return reserva


@transaction.atomic
def crear_reservas_demo(canchas: dict[str, Cancha], usuarios: dict) -> int:
    """Crea dos retenciones y una vencida, solo para el jugador y las canchas demo."""
    fecha = _proximo_lunes()
    jugador = usuarios["jugador"]
    reservas = (
        _crear_reserva_demo(
            jugador, canchas["cancha_a_heredada"], fecha, time(18), 1,
            "retencion-una-hora",
        ),
        _crear_reserva_demo(
            jugador, canchas["cancha_b_centro_1"], fecha, time(19), 2,
            "retencion-multihora-empresa-b",
        ),
        _crear_reserva_demo(
            jugador, canchas["cancha_a_heredada"], fecha, time(21), 1,
            "retencion-vencida-liberada", vencida=True,
        ),
    )
    return {
        "retencion-una-hora": reservas[0],
        "retencion-multihora-empresa-b": reservas[1],
        "retencion-vencida-liberada": reservas[2],
    }
