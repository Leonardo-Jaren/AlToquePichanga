"""Encola avisos transaccionales para el procesador existente de correo."""
from django.conf import settings
from django.utils import timezone

from apps.pagos.services.representacion import importe_pagado
from apps.reservas.models import NotificacionReserva, Reserva
from apps.usuarios.models import CorreoPendiente


def encolar_notificacion_reserva(reserva: Reserva, tipo: str) -> None:
    if NotificacionReserva.objects.filter(reserva=reserva, tipo=tipo).exists():
        return
    pagado = importe_pagado(reserva)
    inicio = timezone.localtime(reserva.inicio).strftime("%d/%m/%Y %H:%M")
    fin = timezone.localtime(reserva.fin).strftime("%H:%M")
    estado = "confirmada" if tipo == "confirmacion" else "cancelada"
    contenido = (
        f"Tu reserva {reserva.codigo} está {estado}.\n"
        f"Sede: {reserva.cancha.sede.nombre}\nCancha: {reserva.cancha.nombre}\n"
        f"Horario: {inicio}-{fin} (hora de Perú)\n"
        f"Total: S/ {reserva.importe_total:.2f}\nPagado: S/ {pagado:.2f}\n"
        f"Saldo pendiente: S/ {max(reserva.importe_total - pagado, 0):.2f}\n"
        f"Consulta tu reserva: {settings.FRONTEND_URL}/mis-reservas\n"
    )
    correo = CorreoPendiente.objects.create(
        destinatario=reserva.jugador.email, asunto=f"Reserva {estado} · AlToque Pichanga", contenido=contenido,
    )
    NotificacionReserva.objects.create(reserva=reserva, tipo=tipo, correo=correo)


def encolar_aviso_reserva(reserva: Reserva, tipo: str, asunto: str, mensaje: str) -> None:
    if NotificacionReserva.objects.filter(reserva=reserva, tipo=tipo).exists():
        return
    correo = CorreoPendiente.objects.create(
        destinatario=reserva.jugador.email, asunto=asunto,
        contenido=f"Reserva {reserva.codigo}: {mensaje}\nConsulta tu reserva: {settings.FRONTEND_URL}/mis-reservas\n",
    )
    NotificacionReserva.objects.create(reserva=reserva, tipo=tipo, correo=correo)


def encolar_vencimiento(reserva: Reserva) -> None:
    encolar_aviso_reserva(
        reserva, "vencimiento", "Reserva vencida · AlToque Pichanga",
        "Venció el plazo y se liberó el horario. Si realizaste un pago, contacta a la sede para revisión.",
    )
