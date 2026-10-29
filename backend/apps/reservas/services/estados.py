from django.db import transaction

from apps.reservas.models import EstadoReserva, HistorialEstadoReserva, Reserva

TRANSICIONES_PERMITIDAS = {
    "": {EstadoReserva.RETENIDA},
    EstadoReserva.RETENIDA: {
        EstadoReserva.PENDIENTE_PAGO, EstadoReserva.VENCIDA, EstadoReserva.CANCELADA,
    },
    EstadoReserva.PENDIENTE_PAGO: {
        EstadoReserva.PENDIENTE_VERIFICACION, EstadoReserva.PENDIENTE_CONFIRMACION,
        EstadoReserva.VENCIDA, EstadoReserva.CANCELADA,
    },
    EstadoReserva.PENDIENTE_VERIFICACION: {
        EstadoReserva.PENDIENTE_PAGO, EstadoReserva.PENDIENTE_CONFIRMACION,
        EstadoReserva.VENCIDA,
    },
    EstadoReserva.PENDIENTE_CONFIRMACION: {
        EstadoReserva.PENDIENTE_PAGO, EstadoReserva.VENCIDA,
    },
}


def cambiar_estado(
    reserva: Reserva, estado_nuevo: str, motivo: str, responsable=None
) -> Reserva:
    if estado_nuevo not in TRANSICIONES_PERMITIDAS.get(reserva.estado, set()):
        raise ValueError(f"Transición de reserva no permitida: {reserva.estado} → {estado_nuevo}.")
    anterior = reserva.estado
    reserva.estado = estado_nuevo
    reserva.save(update_fields=["estado", "actualizada_en"])
    HistorialEstadoReserva.objects.create(
        reserva=reserva,
        estado_anterior=anterior,
        estado_nuevo=estado_nuevo,
        motivo=motivo,
        responsable=responsable,
    )
    return reserva


@transaction.atomic
def cambiar_estado_inicial(reserva: Reserva, motivo: str, responsable=None) -> None:
    HistorialEstadoReserva.objects.create(
        reserva=reserva,
        estado_anterior="",
        estado_nuevo=EstadoReserva.RETENIDA,
        motivo=motivo,
        responsable=responsable,
    )
