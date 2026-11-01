from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.contrib.auth.models import User
from django.db import close_old_connections
from django.utils import timezone

from apps.reservas.models import AsistenciaReserva, EstadoReserva, Reserva
from apps.reservas.services.confirmacion import confirmar_reserva_verificada
from apps.reservas.services.ticket import token_ticket
from tests.test_fase4c_pagos import _api, _contexto
from tests.test_fase4d_confirmacion import _pago_aprobado


def _confirmada_en_curso(nombre):
    contexto = _contexto(nombre)
    _pago_aprobado(contexto)
    reserva, _ = confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    ahora = timezone.now()
    Reserva.objects.filter(pk=reserva.pk).update(inicio=ahora - timedelta(minutes=5), fin=ahora + timedelta(minutes=55))
    reserva.refresh_from_db()
    return contexto, reserva


@pytest.mark.django_db
def test_ingreso_qr_y_manual_valida_alcance_estado_y_duplicados():
    contexto, reserva = _confirmada_en_curso("asistencia")
    otro = _contexto("asistencia-otra")
    url = "/api/reservas/administracion/ingreso/"
    consulta = {"tipo": "qr", "valor": token_ticket(reserva)}
    assert _api(otro["cajero"]).post(url + "consultar/", consulta, format="json").status_code == 404
    assert _api(contexto["jugador"]).post(url + "consultar/", consulta, format="json").status_code == 404
    assert _api(contexto["cajero"]).post(url + "consultar/", {**consulta, "valor": consulta["valor"] + "x"}, format="json").status_code == 400
    respuesta = _api(contexto["cajero"]).post(url + "consultar/", consulta, format="json")
    assert respuesta.status_code == 200
    assert str(respuesta.data["saldo_pendiente"]) == "25.00"
    manual = {"tipo": "codigo", "valor": reserva.codigo}
    assert _api(contexto["cajero"]).post(url + "registrar/", manual, format="json").status_code == 201
    assert _api(contexto["cajero"]).post(url + "registrar/", consulta, format="json").status_code == 409
    assert AsistenciaReserva.objects.filter(reserva=reserva).count() == 1
    Reserva.objects.filter(pk=reserva.pk).update(estado=EstadoReserva.CANCELADA)
    assert _api(contexto["cajero"]).post(url + "consultar/", consulta, format="json").status_code == 400


@pytest.mark.django_db(transaction=True)
def test_ingresos_simultaneos_registran_una_sola_asistencia():
    contexto, reserva = _confirmada_en_curso("asistencia-concurrente")
    barrera = Barrier(2)

    def registrar(_):
        close_old_connections()
        try:
            usuario = User.objects.get(pk=contexto["cajero"].pk)
            cliente = _api(usuario)
            barrera.wait(timeout=10)
            return cliente.post("/api/reservas/administracion/ingreso/registrar/", {"tipo": "codigo", "valor": reserva.codigo}, format="json").status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as grupo:
        assert sorted(grupo.map(registrar, range(2))) == [201, 409]
    assert AsistenciaReserva.objects.filter(reserva=reserva).count() == 1


@pytest.mark.django_db
def test_listado_administrativo_acepta_paginacion_sin_perder_alcance():
    contexto = _contexto("lista-paginada")
    otro = _contexto("lista-ajena")
    respuesta = _api(contexto["cajero"]).get("/api/reservas/administracion/", {"page": 1, "page_size": 25})
    assert respuesta.status_code == 200
    assert [item["codigo"] for item in respuesta.data["results"]] == [contexto["reserva"].codigo]
    assert otro["reserva"].codigo not in str(respuesta.data)
