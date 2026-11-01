"""Ticket privado: la firma contiene solo el código opaco de la reserva."""
from io import BytesIO

import qrcode
import qrcode.image.svg
from django.core import signing
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.pagos.services.representacion import importe_pagado
from apps.reservas.models import EstadoReserva, Reserva

SAL_TICKET = "altoque.reserva.ticket.v1"


def reserva_ticket(jugador, codigo: str) -> Reserva:
    reserva = get_object_or_404(
        Reserva.objects.select_related("jugador", "cancha__sede"),
        codigo=codigo, jugador=jugador,
    )
    if reserva.estado != EstadoReserva.CONFIRMADA:
        raise ValidationError({"estado": "El ticket está disponible cuando la reserva está confirmada."})
    return reserva


def token_ticket(reserva: Reserva) -> str:
    return signing.Signer(salt=SAL_TICKET).sign(reserva.codigo)


def leer_token_ticket(token: str) -> str:
    try:
        return signing.Signer(salt=SAL_TICKET).unsign(token)
    except signing.BadSignature as exc:
        raise ValidationError({"qr": "El código QR no es válido."}) from exc


def datos_ticket(reserva: Reserva) -> dict:
    pagado = importe_pagado(reserva)
    aceptacion = reserva.aceptaciones_cancelacion.order_by("-aceptada_en", "-id").first()
    return {
        "codigo": reserva.codigo, "sede": reserva.cancha.sede.nombre,
        "cancha": reserva.cancha.nombre, "inicio": reserva.inicio, "fin": reserva.fin,
        "jugador": reserva.jugador.get_full_name() or reserva.jugador.username,
        "importe_total": reserva.importe_total, "importe_pagado": pagado,
        "saldo_pendiente": max(reserva.importe_total - pagado, 0),
        "moneda": reserva.moneda, "estado": reserva.estado,
        "condiciones_cancelacion": aceptacion.texto_aceptado if aceptacion else None,
    }


def qr_ticket_svg(reserva: Reserva) -> bytes:
    imagen = qrcode.make(token_ticket(reserva), image_factory=qrcode.image.svg.SvgPathFillImage,
                         box_size=10, border=4)
    salida = BytesIO()
    imagen.save(salida)
    return salida.getvalue()
