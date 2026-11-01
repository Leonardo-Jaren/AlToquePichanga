from uuid import uuid4

import pytest

from apps.pagos.models import (
    AceptacionCancelacion,
    CondicionCancelacionSede,
    PagoReserva,
)
from tests.test_fase4c_pagos import _api, _contexto, _solicitar_pago


@pytest.mark.django_db
def test_pago_exige_version_y_aceptacion_vigente_y_conserva_historico():
    contexto = _contexto("condiciones")
    ruta = f"/api/pagos/reservas/{contexto['reserva'].codigo}/solicitudes/"
    entrada = {"tipo": "adelanto", "metodo_id": contexto["metodo"].pk, "clave_idempotencia": str(uuid4()),
               "version_condiciones": 1, "acepta_condiciones": False}
    jugador = _api(contexto["jugador"])
    assert jugador.post(ruta, entrada, format="json").status_code == 400
    assert not PagoReserva.objects.filter(reserva=contexto["reserva"]).exists()
    assert not AceptacionCancelacion.objects.filter(reserva=contexto["reserva"]).exists()
    entrada["acepta_condiciones"] = True
    assert jugador.post(ruta, entrada, format="json").status_code == 201
    aceptacion = AceptacionCancelacion.objects.get(reserva=contexto["reserva"])
    assert aceptacion.version_aceptada == 1
    texto_anterior = aceptacion.texto_aceptado
    ruta_condicion = f"/api/pagos/sedes/{contexto['sede'].pk}/condiciones/"
    assert _api(contexto["dueno"]).put(ruta_condicion, {"texto": "Nueva condición de prueba"}, format="json").status_code == 200
    aceptacion.refresh_from_db()
    assert aceptacion.texto_aceptado == texto_anterior
    assert CondicionCancelacionSede.objects.filter(sede=contexto["sede"]).count() == 2


@pytest.mark.django_db
def test_cambio_version_y_acceso_entre_empresas():
    contexto = _contexto("condicion-a")
    otro = _contexto("condicion-b")
    ruta = f"/api/pagos/sedes/{contexto['sede'].pk}/condiciones/"
    assert _api(otro["dueno"]).put(ruta, {"texto": "Ajena"}, format="json").status_code == 403
    assert _api(contexto["cajero"]).put(ruta, {"texto": "Ajena"}, format="json").status_code == 403
    assert _api(contexto["dueno"]).put(ruta, {"texto": "Versión nueva de prueba"}, format="json").data["version"] == 2
    respuesta = _solicitar_pago(contexto)
    assert respuesta.status_code == 400
    assert not AceptacionCancelacion.objects.filter(reserva=contexto["reserva"]).exists()
