import socket
from io import StringIO

import pytest
from aiosmtpd.controller import Controller
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from apps.usuarios.models import CorreoPendiente


class BuzonLocal:
    def __init__(self):
        self.mensajes = []

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        if not address.endswith("@example.test"):
            return "550 El servidor local solo acepta destinatarios de prueba."
        envelope.rcpt_tos.append(address)
        return "250 Destinatario de prueba aceptado."

    async def handle_DATA(self, server, session, envelope):
        self.mensajes.append((list(envelope.rcpt_tos), envelope.content))
        return "250 Mensaje de prueba guardado localmente."


def _puerto_libre() -> int:
    with socket.socket() as conexion:
        conexion.bind(("127.0.0.1", 0))
        return conexion.getsockname()[1]


@pytest.mark.django_db
def test_procesador_entrega_cola_a_smtp_local_sin_relay_externo():
    buzon = BuzonLocal()
    servidor = Controller(buzon, hostname="127.0.0.1", port=_puerto_libre())
    servidor.start()
    try:
        correo = CorreoPendiente.objects.create(
            destinatario="jugador@example.test",
            asunto="Reserva de prueba",
            contenido="El QR está listo.",
            proximo_intento=timezone.now(),
        )
        correo_local = {
            "default": {
                "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
                "OPTIONS": {
                    "host": "127.0.0.1",
                    "port": servidor.port,
                    "use_tls": False,
                    "use_ssl": False,
                    "timeout": 3,
                },
            },
        }
        salida = StringIO()
        with override_settings(MAILERS=correo_local):
            call_command("enviar_correos", stdout=salida, stderr=StringIO())
    finally:
        servidor.stop()

    correo.refresh_from_db()
    assert salida.getvalue().strip() == "Correos enviados: 1"
    assert correo.enviado_en is not None
    assert correo.intentos == 1
    assert correo.contenido == ""
    assert len(buzon.mensajes) == 1
    destinatarios, contenido = buzon.mensajes[0]
    assert destinatarios == ["jugador@example.test"]
    assert b"Subject: Reserva de prueba" in contenido
    assert b"El QR est\xc3\xa1 listo." in contenido
