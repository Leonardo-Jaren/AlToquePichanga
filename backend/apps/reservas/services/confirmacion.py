from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.canchas.models import Cancha
from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.services.auditoria import auditar
from apps.pagos.models import EstadoPagoReserva
from apps.pagos.services.representacion import fecha_limite, importe_pagado
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.estados import cambiar_estado
from apps.reservas.services.eventos import programar_cambio_intervalo
from apps.reservas.services.notificaciones import encolar_notificacion_reserva


def _bloques_protegidos(reserva: Reserva) -> bool:
    bloques = list(reserva.bloques.select_for_update().order_by("inicio", "pk"))
    if len(bloques) != reserva.duracion_horas:
        return False
    inicio = reserva.inicio
    for bloque in bloques:
        if (bloque.cancha_id != reserva.cancha_id or bloque.liberado_en is not None
                or bloque.inicio != inicio or bloque.fin != inicio + timedelta(hours=1)):
            return False
        inicio = bloque.fin
    return inicio == reserva.fin


@transaction.atomic
def confirmar_reserva_verificada(usuario, reserva_id: int) -> tuple[Reserva, bool]:
    """Confirma una reserva previamente pagada, sin recuperar bloques liberados.

    El pago debe haberse aprobado dentro de la misma transacción.
    """
    alcance = Reserva.objects.filter(
        pk=reserva_id, cancha__in=canchas_visibles(usuario),
    ).exclude(jugador=usuario).values("pk", "cancha_id").first()
    if alcance is None:
        raise ValidationError({"reserva": "No se encontró una reserva autorizada."})
    Cancha.objects.select_for_update().get(pk=alcance["cancha_id"])
    reserva = Reserva.objects.select_for_update().select_related(
        "cancha__sede__empresa",
    ).get(pk=alcance["pk"])
    if reserva.estado == EstadoReserva.CONFIRMADA:
        return reserva, False
    if reserva.estado != EstadoReserva.PENDIENTE_CONFIRMACION:
        raise ValidationError({"estado": "La reserva no está pendiente de confirmación."})
    if fecha_limite(reserva) <= timezone.now() or reserva.inicio <= timezone.now():
        raise ValidationError({"estado": "La retención o el horario ya venció; requiere revisión manual."})
    pagos = reserva.pagos_reserva.filter(estado=EstadoPagoReserva.APROBADO)
    if pagos.filter(requiere_conciliacion=True).exists() or pagos.exclude(
        metodo__sede_id=reserva.cancha.sede_id
    ).exists():
        raise ValidationError({"pago": "El pago requiere conciliación manual."})
    if importe_pagado(reserva) < reserva.adelanto_minimo:
        raise ValidationError({"pago": "El pago aprobado no alcanza el adelanto mínimo."})
    if not _bloques_protegidos(reserva):
        raise ValidationError({"horario": "El horario no está protegido; requiere revisión manual."})
    cambiar_estado(reserva, EstadoReserva.CONFIRMADA, "Pago verificado y horario protegido.", usuario)
    encolar_notificacion_reserva(reserva, "confirmacion")
    auditar(usuario, "confirmar_reserva", "reserva", reserva.pk, reserva.cancha.sede.empresa)
    programar_cambio_intervalo(reserva.cancha_id, reserva.inicio, reserva.fin, "reserva_confirmada")
    return reserva, True
