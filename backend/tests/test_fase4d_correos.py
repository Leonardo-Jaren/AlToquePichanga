from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.db import transaction

from apps.reservas.models import EstadoReserva, NotificacionReserva
from apps.reservas.services.confirmacion import confirmar_reserva_verificada
from tests.test_fase4c_pagos import _contexto
from tests.test_fase4d_confirmacion import _pago_aprobado


@pytest.mark.django_db
def test_confirmacion_encola_una_vez_y_fallo_smtp_no_retrocede_reserva():
    contexto = _contexto("correo")
    _pago_aprobado(contexto)
    reserva, _ = confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    confirmar_reserva_verificada(contexto["cajero"], reserva.pk)
    assert NotificacionReserva.objects.filter(reserva=reserva, tipo="confirmacion").count() == 1
    notificacion = reserva.notificaciones.get(tipo="confirmacion")
    assert "S/ 25.00" in notificacion.correo.contenido
    with patch("apps.usuarios.management.commands.enviar_correos.send_mail", side_effect=OSError("SMTP")):
        call_command("enviar_correos", stdout=StringIO(), stderr=StringIO())
    reserva.refresh_from_db()
    notificacion.correo.refresh_from_db()
    assert reserva.estado == EstadoReserva.CONFIRMADA
    assert notificacion.correo.enviado_en is None
    assert notificacion.correo.intentos == 1


@pytest.mark.django_db
def test_rollback_no_conserva_aviso_de_confirmacion():
    contexto = _contexto("correo-rollback")
    _pago_aprobado(contexto)
    try:
        with transaction.atomic():
            confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
            raise RuntimeError("rollback")
    except RuntimeError:
        pass
    assert not NotificacionReserva.objects.filter(reserva=contexto["reserva"]).exists()


@pytest.mark.django_db
def test_procesador_envia_una_vez_y_no_reenvia():
    contexto = _contexto("correo-enviado")
    _pago_aprobado(contexto)
    reserva, _ = confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    with patch("apps.usuarios.management.commands.enviar_correos.send_mail", return_value=1) as enviar:
        call_command("enviar_correos", stdout=StringIO(), stderr=StringIO())
        call_command("enviar_correos", stdout=StringIO(), stderr=StringIO())
    assert enviar.call_count == 1
    correo = reserva.notificaciones.get(tipo="confirmacion").correo
    correo.refresh_from_db()
    assert correo.enviado_en is not None


@pytest.mark.django_db
def test_rechazo_y_vencimiento_encolan_avisos_sin_duplicados():
    from datetime import timedelta

    from django.utils import timezone

    from apps.reservas.models import Reserva
    from apps.reservas.services.retenciones import vencer_retenciones_vencidas
    from tests.test_fase4c_pagos import _api, _solicitar_pago

    contexto = _contexto("avisos")
    solicitud = _solicitar_pago(contexto).data
    jugador = _api(contexto["jugador"])
    assert jugador.post(
        f"/api/pagos/reservas/{contexto['reserva'].codigo}/{solicitud['id']}/declarar/", {}, format="json"
    ).status_code == 200
    cajero = _api(contexto["cajero"])
    ruta = f"/api/pagos/administracion/{solicitud['id']}/rechazar/"
    assert cajero.post(ruta, {"motivo": "No se recibió el pago"}, format="json").status_code == 200
    assert cajero.post(ruta, {"motivo": "No se recibió el pago"}, format="json").status_code == 200
    assert NotificacionReserva.objects.filter(reserva=contexto["reserva"], tipo=f"r{solicitud['id']}").count() == 1
    Reserva.objects.filter(pk=contexto["reserva"].pk).update(
        revision_pago_vence_en=timezone.now() - timedelta(seconds=1),
    )
    assert vencer_retenciones_vencidas() == 1
    assert vencer_retenciones_vencidas() == 0
    assert NotificacionReserva.objects.filter(reserva=contexto["reserva"], tipo="vencimiento").count() == 1


@pytest.mark.django_db
def test_solicitud_y_cancelacion_de_retencion_encolan_avisos():
    from django.contrib.auth.models import User
    from rest_framework.test import APIClient

    from apps.reservas.models import Reserva
    from tests.test_fase4a_reservas import _contexto as contexto_horarios
    from tests.test_fase4a_reservas import _solicitar as solicitar_retencion

    jugador = User.objects.create_user(username="aviso-retencion@example.test", email="aviso-retencion@example.test")
    _, _, _, cancha, dia = contexto_horarios("dueno-aviso@example.test")
    cliente = APIClient()
    cliente.force_authenticate(jugador)
    from uuid import uuid4

    clave = uuid4()
    respuesta = solicitar_retencion(cliente, cancha, dia, clave=clave)
    assert respuesta.status_code == 201
    reserva = Reserva.objects.get(codigo=respuesta.data["codigo"])
    assert solicitar_retencion(cliente, cancha, dia, clave=clave).status_code == 200
    assert reserva.notificaciones.filter(tipo="solicitud").count() == 1
    assert cliente.post(f"/api/reservas/{reserva.codigo}/cancelar/", {}, format="json").status_code == 200
    assert reserva.notificaciones.filter(tipo="cancelacion").count() == 1
