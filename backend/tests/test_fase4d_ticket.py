
import pytest
from rest_framework.exceptions import ValidationError

from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.confirmacion import confirmar_reserva_verificada
from apps.reservas.services.ticket import leer_token_ticket, token_ticket
from tests.test_fase4c_pagos import _api, _contexto
from tests.test_fase4d_confirmacion import _pago_aprobado


@pytest.mark.django_db
def test_ticket_solo_para_reserva_confirmada_y_su_jugador():
    contexto = _contexto("ticket")
    otro = _contexto("otro-ticket")
    ruta = f"/api/reservas/{contexto['reserva'].codigo}/ticket/"
    assert _api(contexto["jugador"]).get(ruta).status_code == 400
    _pago_aprobado(contexto)
    confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    respuesta = _api(contexto["jugador"]).get(ruta)
    assert respuesta.status_code == 200
    assert str(respuesta.data["saldo_pendiente"]) == "25.00"
    assert _api(otro["jugador"]).get(ruta).status_code == 404
    imagen = _api(contexto["jugador"]).get(ruta + "qr/")
    assert imagen.status_code == 200
    assert imagen["Content-Type"] == "image/svg+xml"
    assert imagen["Cache-Control"] == "no-store"
    assert b"<svg" in imagen.content
    Reserva.objects.filter(pk=contexto["reserva"].pk).update(estado=EstadoReserva.CANCELADA)
    assert _api(contexto["jugador"]).get(ruta + "qr/").status_code == 400


@pytest.mark.django_db
def test_token_firmado_no_contiene_datos_privados_y_no_admite_manipulacion():
    contexto = _contexto("firma")
    reserva = contexto["reserva"]
    token = token_ticket(reserva)
    assert reserva.jugador.email not in token
    assert leer_token_ticket(token) == reserva.codigo
    with pytest.raises(ValidationError):
        leer_token_ticket(token + "x")
