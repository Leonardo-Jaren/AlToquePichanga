from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.pagos.models import EstadoPagoReserva, PagoReserva
from apps.reservas.models import EstadoReserva, Reserva
from apps.reservas.services.confirmacion import confirmar_reserva_verificada
from tests.test_fase4c_pagos import _api, _contexto, _solicitar_pago


def _pago_aprobado(contexto):
    pago = _solicitar_pago(contexto).data
    jugador = _api(contexto["jugador"])
    declaracion = jugador.post(
        f"/api/pagos/reservas/{contexto['reserva'].codigo}/{pago['id']}/declarar/", {}, format="json"
    )
    assert declaracion.status_code == 200
    # Pago aprobado por la versión anterior, antes de conectar la confirmación.
    modelo = PagoReserva.objects.get(pk=pago["id"])
    modelo.estado = EstadoPagoReserva.APROBADO
    modelo.importe_verificado = Decimal("25.00")
    modelo.revisor = contexto["cajero"]
    modelo.revisado_en = timezone.now()
    modelo.save(update_fields=["estado", "importe_verificado", "revisor", "revisado_en"])
    Reserva.objects.filter(pk=contexto["reserva"].pk).update(estado=EstadoReserva.PENDIENTE_CONFIRMACION)
    contexto["reserva"].refresh_from_db()
    return modelo


@pytest.mark.django_db
def test_confirmacion_segura_es_idempotente_y_conserva_importes():
    contexto = _contexto("4d")
    _pago_aprobado(contexto)
    reserva, creada = confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    assert creada and reserva.estado == EstadoReserva.CONFIRMADA
    assert reserva.importe_total == Decimal("50.00")
    assert reserva.adelanto_minimo == Decimal("25.00")
    _, creada = confirmar_reserva_verificada(contexto["cajero"], reserva.pk)
    assert not creada
    assert reserva.historial_estados.filter(estado_nuevo=EstadoReserva.CONFIRMADA).count() == 1


@pytest.mark.django_db
def test_rechaza_acceso_cruzado_y_bloques_liberados():
    contexto = _contexto("4d-a")
    otro = _contexto("4d-b")
    _pago_aprobado(contexto)
    with pytest.raises(ValidationError):
        confirmar_reserva_verificada(otro["cajero"], contexto["reserva"].pk)
    contexto["reserva"].bloques.update(liberado_en=timezone.now())
    with pytest.raises(ValidationError):
        confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    contexto["reserva"].refresh_from_db()
    assert contexto["reserva"].estado == EstadoReserva.PENDIENTE_CONFIRMACION


@pytest.mark.django_db
def test_rechaza_pago_insuficiente_y_retencion_vencida():
    contexto = _contexto("4d-c")
    pago = _pago_aprobado(contexto)
    pago.importe_verificado = Decimal("1.00")
    pago.save(update_fields=["importe_verificado"])
    with pytest.raises(ValidationError):
        confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    pago.importe_verificado = Decimal("25.00")
    pago.save(update_fields=["importe_verificado"])
    contexto["reserva"].revision_pago_vence_en = timezone.now() - timedelta(seconds=1)
    contexto["reserva"].save(update_fields=["revision_pago_vence_en"])
    with pytest.raises(ValidationError):
        confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)


@pytest.mark.django_db
def test_aprobacion_sin_bloque_activo_guarda_pago_para_conciliacion():
    contexto = _contexto("4d-incidencia")
    solicitud = _solicitar_pago(contexto).data
    ruta = f"/api/pagos/reservas/{contexto['reserva'].codigo}/{solicitud['id']}/declarar/"
    assert _api(contexto["jugador"]).post(ruta, {}, format="json").status_code == 200
    contexto["reserva"].bloques.update(liberado_en=timezone.now())
    respuesta = _api(contexto["cajero"]).post(
        f"/api/pagos/administracion/{solicitud['id']}/aprobar/", {}, format="json"
    )
    assert respuesta.status_code == 409
    pago = PagoReserva.objects.get(pk=solicitud["id"])
    assert pago.estado == EstadoPagoReserva.APROBADO
    assert pago.requiere_conciliacion
    contexto["reserva"].refresh_from_db()
    assert contexto["reserva"].estado != EstadoReserva.CONFIRMADA
    assert pago.historial.filter(motivo__icontains="conciliación").exists()


@pytest.mark.django_db
def test_confirmacion_publica_aviso_solo_despues_del_commit(django_capture_on_commit_callbacks):
    from unittest.mock import patch

    contexto = _contexto("4d-evento")
    _pago_aprobado(contexto)
    with patch("apps.reservas.services.eventos._publicar") as publicar:
        with django_capture_on_commit_callbacks(execute=True) as callbacks:
            confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
            assert not publicar.called
        assert callbacks
        assert publicar.called


@pytest.mark.django_db(transaction=True)
def test_aprobaciones_simultaneas_solo_confirman_una_vez():
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.contrib.auth.models import User
    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("La concurrencia requiere PostgreSQL.")
    contexto = _contexto("4d-concurrente")
    pago = _solicitar_pago(contexto).data
    ruta = f"/api/pagos/reservas/{contexto['reserva'].codigo}/{pago['id']}/declarar/"
    assert _api(contexto["jugador"]).post(ruta, {}, format="json").status_code == 200
    barrera = Barrier(2)

    def aprobar(_):
        close_old_connections()
        try:
            cajero = User.objects.get(pk=contexto["cajero"].pk)
            cliente = _api(cajero)
            barrera.wait(timeout=10)
            return cliente.post(f"/api/pagos/administracion/{pago['id']}/aprobar/", {}, format="json").status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as grupo:
        resultados = list(grupo.map(aprobar, range(2)))
    assert resultados == [200, 200]
    reserva = Reserva.objects.get(pk=contexto["reserva"].pk)
    assert reserva.estado == EstadoReserva.CONFIRMADA
    assert reserva.historial_estados.filter(estado_nuevo=EstadoReserva.CONFIRMADA).count() == 1
    assert PagoReserva.objects.filter(reserva=reserva, estado=EstadoPagoReserva.APROBADO).count() == 1


@pytest.mark.django_db
def test_aprobacion_tardia_conserva_pago_y_exige_conciliacion():
    contexto = _contexto("4d-pago-tardio")
    solicitud = _solicitar_pago(contexto).data
    jugador = _api(contexto["jugador"])
    ruta = f"/api/pagos/reservas/{contexto['reserva'].codigo}/{solicitud['id']}/declarar/"
    assert jugador.post(ruta, {}, format="json").status_code == 200
    Reserva.objects.filter(pk=contexto["reserva"].pk).update(
        revision_pago_vence_en=timezone.now() - timedelta(seconds=1),
    )
    respuesta = _api(contexto["cajero"]).post(
        f"/api/pagos/administracion/{solicitud['id']}/aprobar/", {}, format="json"
    )
    assert respuesta.status_code == 409
    pago = PagoReserva.objects.get(pk=solicitud["id"])
    contexto["reserva"].refresh_from_db()
    assert pago.estado == EstadoPagoReserva.APROBADO
    assert pago.importe_verificado == Decimal("25.00")
    assert pago.requiere_conciliacion
    assert contexto["reserva"].estado == EstadoReserva.VENCIDA
    assert contexto["reserva"].bloques.filter(liberado_en__isnull=True).count() == 0
