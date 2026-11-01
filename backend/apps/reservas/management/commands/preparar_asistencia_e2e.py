"""Ajusta solo el horario de una reserva demo para la E2E de asistencia local."""

import json
import os
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.ticket import token_ticket
from apps.usuarios.services.datos_demo import CORREOS, MARCA


def _validar_entorno() -> None:
    if settings.DEBUG is not True:
        raise CommandError("El control horario E2E solo se permite con DEBUG=True.")
    if os.environ.get("ALTOQUE_PERMITIR_E2E_ASISTENCIA") != "1":
        raise CommandError("Define ALTOQUE_PERMITIR_E2E_ASISTENCIA=1 para permitir este ajuste local.")
    base = settings.DATABASES.get("default", {})
    if base.get("ENGINE") != "django.db.backends.postgresql":
        raise CommandError("El escenario requiere PostgreSQL local.")
    if str(base.get("HOST", "")).strip().casefold() not in {"localhost", "127.0.0.1", "::1"}:
        raise CommandError("El escenario solo permite una base PostgreSQL de loopback.")


def _fecha(valor: str | None) -> datetime:
    if not valor:
        raise CommandError("Falta una fecha y hora requerida para restaurar la reserva.")
    try:
        fecha = datetime.fromisoformat(valor)
    except ValueError as exc:
        raise CommandError("La fecha y hora debe estar en formato ISO 8601.") from exc
    if timezone.is_naive(fecha):
        raise CommandError("La fecha y hora debe incluir zona horaria.")
    return fecha


class Command(BaseCommand):
    help = "Controla el horario de una reserva demo para probar asistencia sin cambiar el reloj."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--codigo", required=True)
        parser.add_argument("--restaurar", action="store_true")
        parser.add_argument("--inicio-original")
        parser.add_argument("--fin-original")
        parser.add_argument("--inicio-controlado")
        parser.add_argument("--fin-controlado")

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        _validar_entorno()
        reserva = Reserva.objects.select_for_update().select_related(
            "jugador", "cancha", "cancha__sede__empresa",
        ).filter(codigo=options["codigo"]).first()
        if (
            reserva is None
            or reserva.estado != EstadoReserva.CONFIRMADA
            or reserva.jugador.email != CORREOS["jugador"]
            or not reserva.cancha.nombre.startswith(f"{MARCA} Cancha")
            or not reserva.cancha.sede.empresa.descripcion.startswith(MARCA)
        ):
            raise CommandError("Solo se puede ajustar una reserva confirmada de las cuentas demo locales.")

        ahora = timezone.now()
        if options["restaurar"]:
            inicio_original = _fecha(options["inicio_original"])
            fin_original = _fecha(options["fin_original"])
            inicio_controlado = _fecha(options["inicio_controlado"])
            fin_controlado = _fecha(options["fin_controlado"])
            if (reserva.inicio, reserva.fin) != (inicio_controlado, fin_controlado):
                raise CommandError("La reserva cambió desde que se preparó; se conservó su horario actual.")
            if inicio_original <= ahora or fin_original <= inicio_original:
                raise CommandError("El horario original no es futuro o no forma un intervalo válido.")
            inicio, fin = inicio_original, fin_original
        else:
            if reserva.inicio <= ahora:
                raise CommandError("La reserva demo debe estar en el futuro antes del ajuste.")
            inicio = ahora - timedelta(minutes=5)
            fin = inicio + timedelta(hours=reserva.duracion_horas)
            datos = {
                "inicio_original": reserva.inicio.isoformat(),
                "fin_original": reserva.fin.isoformat(),
                "inicio_controlado": inicio.isoformat(),
                "fin_controlado": fin.isoformat(),
                "token_qr": token_ticket(reserva),
            }
            Reserva.objects.filter(pk=reserva.pk).update(
                inicio=inicio, fin=fin, actualizada_en=ahora,
            )
            self.stdout.write(json.dumps(datos))
            return

        Reserva.objects.filter(pk=reserva.pk).update(
            inicio=inicio, fin=fin, actualizada_en=ahora,
        )
        self.stdout.write("Horario original restaurado.")
