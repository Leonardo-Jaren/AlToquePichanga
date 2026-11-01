from uuid import uuid4

import pytest

from apps.canchas.models import Cancha
from apps.empresas.models import RegistroAuditoria
from apps.pagos.models import MetodoPagoSede
from apps.usuarios.services.datos_demo import MARCA
from tests.test_fase4a_reservas import _proximo_dia
from tests.test_usuarios_prueba import _generar, _iniciar_sesion


@pytest.mark.django_db
def test_flujo_4d_con_sesiones_reales_y_alcance_por_rol(monkeypatch, tmp_path, settings):
    settings.DEBUG = True
    settings.PAGOS_RESERVA_HABILITADOS = True
    credenciales = _generar(monkeypatch, tmp_path)
    cancha = Cancha.objects.get(nombre=f"{MARCA} Cancha A heredada")
    jugador, _, csrf = _iniciar_sesion("jugador", credenciales)
    respuesta = jugador.post("/api/reservas/", {
        "cancha_id": cancha.pk, "fecha": _proximo_dia(0).isoformat(), "hora_inicio": "18:00",
        "duracion_horas": 1, "clave_idempotencia": str(uuid4()),
    }, format="json", HTTP_X_CSRFTOKEN=csrf)
    assert respuesta.status_code == 201, respuesta.data
    codigo = respuesta.data["codigo"]
    metodo = MetodoPagoSede.objects.filter(sede=cancha.sede, activo=True).first()
    solicitud = jugador.post(f"/api/pagos/reservas/{codigo}/solicitudes/", {
        "tipo": "adelanto", "metodo_id": metodo.pk, "clave_idempotencia": str(uuid4()),
        "acepta_condiciones": True, "version_condiciones": 1,
    }, format="json", HTTP_X_CSRFTOKEN=csrf)
    assert solicitud.status_code == 201, solicitud.data
    pago_id = solicitud.data["id"]
    assert jugador.post(f"/api/pagos/reservas/{codigo}/{pago_id}/declarar/", {}, format="json", HTTP_X_CSRFTOKEN=csrf).status_code == 200
    cajero, _, csrf_cajero = _iniciar_sesion("cajero_a", credenciales)
    assert cajero.post(f"/api/pagos/administracion/{pago_id}/aprobar/", {}, format="json", HTTP_X_CSRFTOKEN=csrf_cajero).status_code == 200
    assert jugador.get(f"/api/reservas/{codigo}/ticket/").status_code == 200
    otro_jugador, _, _ = _iniciar_sesion("jugador_b", credenciales)
    assert otro_jugador.get(f"/api/reservas/{codigo}/ticket/").status_code == 404
    ruta = f"/api/reservas/administracion/{codigo}/"
    for rol in ("cajero_a", "admin_a", "dueno_a", "superadmin"):
        cliente, _, _ = _iniciar_sesion(rol, credenciales)
        assert cliente.get(ruta).status_code == 200
    dueno_ajeno, _, _ = _iniciar_sesion("dueno_b", credenciales)
    assert dueno_ajeno.get(ruta).status_code == 404
    assert jugador.get(ruta).status_code == 403
    assert RegistroAuditoria.objects.filter(accion="consultar_reserva_global").exists()
