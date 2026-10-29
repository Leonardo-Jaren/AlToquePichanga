from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.canchas.models import Cancha
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.estados import cambiar_estado
from apps.reservas.services.eventos import (
    fechas_en_intervalo,
    programar_cambio_disponibilidad,
)

ESTADOS_VENCIBLES = (
    EstadoReserva.RETENIDA,
    EstadoReserva.PENDIENTE_PAGO,
    EstadoReserva.PENDIENTE_VERIFICACION,
    EstadoReserva.PENDIENTE_CONFIRMACION,
)


def _vencer_de_cancha(cancha_id: int, ahora) -> int:
    vencidas = Reserva.objects.select_for_update().filter(
        cancha_id=cancha_id,
        estado__in=ESTADOS_VENCIBLES,
    ).filter(
        Q(revision_pago_vence_en__lte=ahora)
        | Q(revision_pago_vence_en__isnull=True, retencion_vence_en__lte=ahora)
    ).order_by("pk")
    cantidad = 0
    fechas_afectadas = set()
    for reserva in vencidas:
        motivo = "Venció el plazo de pago o revisión manual."
        cambiar_estado(reserva, EstadoReserva.VENCIDA, motivo)
        reserva.bloques.filter(liberado_en__isnull=True).update(liberado_en=ahora)
        from apps.pagos.services.pagos import cerrar_pagos_vencidos

        cerrar_pagos_vencidos(reserva, ahora)
        fechas_afectadas.update(fechas_en_intervalo(reserva.inicio, reserva.fin))
        cantidad += 1
    for fecha in fechas_afectadas:
        programar_cambio_disponibilidad(cancha_id, fecha, "retencion_vencida")
    return cantidad


@transaction.atomic
def vencer_retenciones_de_cancha(cancha_id: int, ahora=None) -> int:
    ahora = ahora or timezone.now()
    list(Cancha.objects.select_for_update().filter(pk=cancha_id))
    return _vencer_de_cancha(cancha_id, ahora)


@transaction.atomic
def vencer_retenciones_vencidas(ahora=None) -> int:
    ahora = ahora or timezone.now()
    canchas = Reserva.objects.filter(
        estado__in=ESTADOS_VENCIBLES,
    ).filter(
        Q(revision_pago_vence_en__lte=ahora)
        | Q(revision_pago_vence_en__isnull=True, retencion_vence_en__lte=ahora)
    ).values_list("cancha_id", flat=True).distinct().order_by("cancha_id")
    ids = list(canchas)
    list(Cancha.objects.select_for_update().filter(pk__in=ids).order_by("pk"))
    return sum(_vencer_de_cancha(cancha_id, ahora) for cancha_id in ids)
