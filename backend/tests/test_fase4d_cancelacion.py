from unittest.mock import patch

import pytest

from apps.pagos.models import EstadoPagoReserva
from apps.reservas.models import EstadoReserva, NotificacionReserva
from apps.reservas.services.confirmacion import confirmar_reserva_verificada
from tests.test_fase4c_pagos import _api, _contexto
from tests.test_fase4d_confirmacion import _pago_aprobado


@pytest.mark.django_db
def test_cancelacion_propietario_preserva_pago_y_libera_despues_de_commit(django_capture_on_commit_callbacks):
    contexto = _contexto("cancelacion")
    pago = _pago_aprobado(contexto)
    reserva, _ = confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    ruta = f"/api/reservas/{reserva.codigo}/cancelacion/"
    with patch("apps.reservas.services.eventos._publicar") as publicar:
        with django_capture_on_commit_callbacks(execute=True):
            respuesta = _api(contexto["jugador"]).post(ruta, {"motivo": "Cambio de planes"}, format="json")
            assert respuesta.status_code == 200
            assert respuesta.data["requiere_revision"]
            assert not publicar.called
        assert publicar.called
    reserva.refresh_from_db()
    pago.refresh_from_db()
    assert reserva.estado == EstadoReserva.CANCELADA
    assert reserva.bloques.filter(liberado_en__isnull=False).count() == 1
    assert pago.estado == EstadoPagoReserva.APROBADO and pago.requiere_conciliacion
    assert NotificacionReserva.objects.filter(reserva=reserva, tipo="cancelacion").count() == 1
    assert _api(contexto["jugador"]).post(ruta, {"motivo": "Reintento"}, format="json").status_code == 200
    assert NotificacionReserva.objects.filter(reserva=reserva, tipo="cancelacion").count() == 1


@pytest.mark.django_db
def test_cancelacion_administrativa_requiere_alcance_y_motivo():
    contexto = _contexto("cancel-admin")
    otro = _contexto("cancel-otro")
    _pago_aprobado(contexto)
    reserva, _ = confirmar_reserva_verificada(contexto["cajero"], contexto["reserva"].pk)
    ruta = f"/api/reservas/administracion/{reserva.codigo}/cancelar/"
    assert _api(contexto["dueno"]).post(ruta, {}, format="json").status_code == 400
    assert _api(otro["dueno"]).post(ruta, {"motivo": "Cierre"}, format="json").status_code == 404
    assert _api(contexto["cajero"]).post(ruta, {"motivo": "Cierre"}, format="json").status_code == 404
    assert _api(contexto["dueno"]).post(ruta, {"motivo": "Cierre"}, format="json").status_code == 200
    reserva.refresh_from_db()
    assert reserva.estado == EstadoReserva.CANCELADA
    assert reserva.historial_estados.filter(estado_nuevo=EstadoReserva.CANCELADA, responsable=contexto["dueno"]).exists()


@pytest.mark.django_db
def test_cancelacion_con_comprobante_declarado_exige_revision_sin_borrar_pago():
    from apps.pagos.models import PagoReserva
    from tests.test_fase4c_pagos import _solicitar_pago

    contexto = _contexto("cancelacion-pendiente")
    pago = _solicitar_pago(contexto).data
    jugador = _api(contexto["jugador"])
    declarar = f"/api/pagos/reservas/{contexto['reserva'].codigo}/{pago['id']}/declarar/"
    assert jugador.post(declarar, {}, format="json").status_code == 200
    respuesta = jugador.post(
        f"/api/reservas/{contexto['reserva'].codigo}/cancelacion/", {"motivo": "Prueba"}, format="json"
    )
    assert respuesta.status_code == 200
    assert respuesta.data["requiere_revision"]
    guardado = PagoReserva.objects.get(pk=pago["id"])
    assert guardado.requiere_conciliacion
    assert guardado.historial.count() >= 3
