"""Cancelación transaccional sin devolución automática."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.canchas.models import Cancha
from apps.empresas.repositories.alcance import sedes_administrables
from apps.empresas.services.auditoria import auditar
from apps.pagos.models import EstadoPagoReserva, HistorialPagoReserva
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.estados import cambiar_estado
from apps.reservas.services.eventos import programar_cambio_intervalo
from apps.reservas.services.notificaciones import encolar_notificacion_reserva


def _cerrar_pagos(reserva, actor) -> bool:
    requiere_revision = False
    for pago in reserva.pagos_reserva.select_for_update().all():
        anterior = pago.estado
        if pago.estado in {EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION}:
            pago.estado = EstadoPagoReserva.VENCIDO
            if anterior == EstadoPagoReserva.PENDIENTE_REVISION:
                pago.requiere_conciliacion = True
                requiere_revision = True
            pago.save(update_fields=["estado", "requiere_conciliacion"])
            motivo = "La solicitud de pago se cerró al cancelar la reserva; revisar los comprobantes declarados."
        elif pago.estado == EstadoPagoReserva.APROBADO:
            requiere_revision = True
            if pago.requiere_conciliacion:
                continue
            pago.requiere_conciliacion = True
            pago.save(update_fields=["requiere_conciliacion"])
            motivo = "Reserva cancelada con pago aprobado; requiere revisión administrativa."
        else:
            continue
        HistorialPagoReserva.objects.create(
            pago=pago, estado_anterior=anterior, estado_nuevo=pago.estado, motivo=motivo, actor=actor,
        )
    return requiere_revision


@transaction.atomic
def cancelar_reserva(usuario, codigo: str, motivo: str, *, administrativa: bool = False) -> tuple[Reserva, bool]:
    alcance = Reserva.objects.filter(cancha__sede_id__in=sedes_administrables(usuario).values("pk")).exclude(jugador=usuario) if administrativa else Reserva.objects.filter(jugador=usuario)
    referencia = get_object_or_404(alcance, codigo=codigo)
    Cancha.objects.select_for_update().get(pk=referencia.cancha_id)
    reserva = get_object_or_404(alcance.select_for_update(of=("self",)).select_related("cancha__sede__empresa", "jugador"), pk=referencia.pk)
    if reserva.estado == EstadoReserva.CANCELADA:
        return reserva, reserva.pagos_reserva.filter(requiere_conciliacion=True).exists()
    permitidos = {
        EstadoReserva.RETENIDA, EstadoReserva.PENDIENTE_PAGO, EstadoReserva.PENDIENTE_VERIFICACION,
        EstadoReserva.PENDIENTE_CONFIRMACION, EstadoReserva.CONFIRMADA,
    }
    if reserva.estado not in permitidos or reserva.inicio <= timezone.now():
        raise ValidationError({"estado": "Esta reserva no admite cancelación; contacta a la sede para revisión."})
    if reserva.estado != EstadoReserva.CONFIRMADA:
        limite = reserva.revision_pago_vence_en or reserva.retencion_vence_en
        if limite <= timezone.now():
            raise ValidationError({"estado": "La retención venció; contacta a la sede para revisión."})
    if not motivo.strip():
        raise ValidationError({"motivo": "Indica el motivo de la cancelación."})
    revision = _cerrar_pagos(reserva, usuario)
    cambiar_estado(reserva, EstadoReserva.CANCELADA, motivo.strip(), usuario)
    reserva.bloques.filter(liberado_en__isnull=True).update(liberado_en=timezone.now())
    encolar_notificacion_reserva(reserva, "cancelacion")
    auditar(usuario, "cancelar_reserva", "reserva", reserva.pk, reserva.cancha.sede.empresa,
            {"motivo": motivo.strip(), "requiere_revision": revision, "administrativa": administrativa})
    programar_cambio_intervalo(reserva.cancha_id, reserva.inicio, reserva.fin, "reserva_cancelada")
    return reserva, revision
