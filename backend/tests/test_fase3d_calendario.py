from datetime import datetime, time, timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.canchas.models import Cancha, EstadoCancha
from apps.empresas.models import Empresa, MembresiaEmpresa, RolEmpresa
from apps.horarios.models import ExcepcionHorario, TipoExcepcionHorario
from apps.sedes.models import AsignacionSede, Sede
from tests.test_fase3c_tarifas import _contexto, _horario, _proximo_dia, _regla

pytestmark = pytest.mark.django_db


def test_publicacion_explicita_aislamiento_y_datos_publicos_minimos():
    propietario, _, sede, cancha, api = _contexto("dueno-calendario@example.test")
    anonimo = APIClient()
    assert anonimo.get("/api/publico/canchas/").data == []

    publicada = api.patch(
        f"/api/canchas/{cancha.pk}/", {"publicada": True}, format="json"
    )
    assert publicada.status_code == 200, publicada.data
    assert publicada.data["publicada"] is True

    otra_empresa = Empresa.objects.create(nombre="Empresa fuera de alcance")
    otra_sede = Sede.objects.create(
        empresa=otra_empresa, nombre="Sede privada", direccion="Dirección privada",
        telefono_contacto="999999999", correo_contacto="privado@example.test",
    )
    otra_cancha = Cancha.objects.create(
        sede=otra_sede, nombre="Cancha publicada B", modalidad=7,
        tipo_superficie="Sintético", publicada=True,
    )

    listado = anonimo.get("/api/publico/canchas/")
    assert listado.status_code == 200
    assert {item["id"] for item in listado.data} == {cancha.pk, otra_cancha.pk}
    datos_publicos = listado.data[0]
    assert set(datos_publicos) == {
        "id", "nombre", "descripcion", "modalidad", "tipo_superficie",
        "capacidad_jugadores", "techada", "iluminacion", "caracteristicas",
        "estado", "imagen_principal_url", "imagenes", "sede",
    }
    assert set(datos_publicos["sede"]) == {"nombre", "distrito", "provincia", "departamento"}
    assert "direccion" not in datos_publicos["sede"]
    assert api.get(f"/api/canchas/{otra_cancha.pk}/").status_code == 404

    cajero = User.objects.create_user(username="cajero-calendario", password="test")
    membresia = MembresiaEmpresa.objects.create(
        usuario=cajero, empresa=sede.empresa, rol=RolEmpresa.CAJERO,
    )
    AsignacionSede.objects.create(sede=sede, membresia=membresia)
    consulta_cajero = APIClient()
    consulta_cajero.force_authenticate(cajero)
    respuesta = consulta_cajero.patch(
        f"/api/canchas/{cancha.pk}/", {"publicada": False}, format="json"
    )
    assert respuesta.status_code == 403
    assert propietario.is_authenticated


def test_disponibilidad_publica_integra_tarifas_cierres_y_ampliaciones():
    propietario, _, sede, cancha, api = _contexto("dueno-integracion-calendario@example.test")
    cancha.publicada = True
    cancha.save(update_fields=["publicada"])
    fecha = _proximo_dia(4)
    _horario(sede, fecha.weekday(), "18:00", "20:00")
    zona = timezone.get_current_timezone()
    inicio_cierre = timezone.make_aware(datetime.combine(fecha, time(19)), zona)
    inicio_ampliacion = timezone.make_aware(datetime.combine(fecha, time(20)), zona)
    ExcepcionHorario.objects.create(
        sede=sede, cancha=cancha, tipo=TipoExcepcionHorario.CIERRE,
        fecha_inicio=inicio_cierre, fecha_fin=inicio_cierre + timedelta(hours=1),
        motivo="Nota interna que no debe mostrarse públicamente", creado_por=propietario,
    )
    ExcepcionHorario.objects.create(
        sede=sede, cancha=cancha, tipo=TipoExcepcionHorario.AMPLIACION,
        fecha_inicio=inicio_ampliacion, fecha_fin=inicio_ampliacion + timedelta(hours=2),
        motivo="Extensión", creado_por=propietario,
    )
    tarifa = api.post(f"/api/canchas/{cancha.pk}/tarifas/", _regla(
        "50.00", dias=[fecha.weekday()], inicio="18:00", fin="22:00",
    ), format="json")
    assert tarifa.status_code == 201, tarifa.data

    anonimo = APIClient()
    respuesta = anonimo.get(
        f"/api/publico/canchas/{cancha.pk}/disponibilidad/",
        {"desde": fecha.isoformat(), "hasta": fecha.isoformat()},
    )
    assert respuesta.status_code == 200, respuesta.data
    assert respuesta.data["considera_reservas"] is True
    bloques = {bloque["fecha_inicio"][11:16]: bloque for bloque in respuesta.data["bloques"]}
    assert bloques["18:00"]["precio"] == "50.00"
    assert bloques["18:00"]["origen"] == "horario_semanal"
    assert bloques["19:00"]["estado"] == "cerrada"
    assert bloques["19:00"]["precio"] is None
    assert "Nota interna" not in bloques["19:00"]["motivo"]
    assert bloques["20:00"]["precio"] == "50.00"
    assert bloques["20:00"]["origen"] == "ampliacion_excepcional"

    cotizacion_cerrada = anonimo.post(
        f"/api/publico/canchas/{cancha.pk}/cotizar/",
        {"fecha": fecha.isoformat(), "hora_inicio": "18:00", "duracion_horas": 2},
        format="json",
    )
    assert cotizacion_cerrada.status_code == 400
    assert "Nota interna" not in str(cotizacion_cerrada.data)


def test_cotizacion_publica_cruza_medianoche_con_el_mismo_motor_decimal():
    propietario, _, sede, cancha, api = _contexto("dueno-cotizacion-calendario@example.test")
    cancha.publicada = True
    cancha.save(update_fields=["publicada"])
    viernes = _proximo_dia(4)
    _horario(sede, viernes.weekday(), "22:00", "02:00")
    tarifa = api.post(f"/api/canchas/{cancha.pk}/tarifas/", _regla(
        "33.33", tipo="nocturna", dias=[viernes.weekday()], inicio="21:00", fin="03:00",
    ), format="json")
    assert tarifa.status_code == 201, tarifa.data

    anonimo = APIClient()
    cotizacion = anonimo.post(
        f"/api/publico/canchas/{cancha.pk}/cotizar/",
        {"fecha": viernes.isoformat(), "hora_inicio": "23:00", "duracion_horas": 2},
        format="json",
    )
    assert cotizacion.status_code == 200, cotizacion.data
    assert [bloque["fecha_inicio"][:16] for bloque in cotizacion.data["bloques"]] == [
        f"{viernes.isoformat()}T23:00",
        f"{(viernes + timedelta(days=1)).isoformat()}T00:00",
    ]
    assert cotizacion.data["total"] == "66.66"
    assert cotizacion.data["moneda"] == "PEN"

    cliente_con_sesion = APIClient(enforce_csrf_checks=True)
    cliente_con_sesion.force_login(propietario)
    cotizacion_con_sesion = cliente_con_sesion.post(
        f"/api/publico/canchas/{cancha.pk}/cotizar/",
        {"fecha": viernes.isoformat(), "hora_inicio": "23:00", "duracion_horas": 2},
        format="json",
    )
    assert cotizacion_con_sesion.status_code == 200, cotizacion_con_sesion.data
    assert cotizacion_con_sesion.data["total"] == "66.66"


def test_cancha_en_mantenimiento_no_muestra_bloques_contratables():
    _, _, sede, cancha, _ = _contexto("dueno-mantenimiento-calendario@example.test")
    cancha.publicada = True
    cancha.estado = EstadoCancha.MANTENIMIENTO
    cancha.save(update_fields=["publicada", "estado"])
    fecha = _proximo_dia(0)
    _horario(sede, fecha.weekday(), "18:00", "20:00")

    anonimo = APIClient()
    respuesta = anonimo.get(
        f"/api/publico/canchas/{cancha.pk}/disponibilidad/",
        {"desde": fecha.isoformat(), "hasta": fecha.isoformat()},
    )
    assert respuesta.status_code == 200, respuesta.data
    assert all(not bloque["habilitada_operativamente"] for bloque in respuesta.data["bloques"])
    assert all(bloque["precio"] is None for bloque in respuesta.data["bloques"])
    assert all(bloque["estado"] == "mantenimiento" for bloque in respuesta.data["bloques"])


def test_fecha_pasada_se_muestra_cerrada_y_la_cancha_inactiva_se_oculta():
    _, _, sede, cancha, api = _contexto("dueno-fecha-pasada-calendario@example.test")
    ayer_semana = timezone.localdate() - timedelta(days=7)
    _horario(sede, ayer_semana.weekday(), "18:00", "19:00")
    cancha.publicada = True
    cancha.save(update_fields=["publicada"])
    operacion = api.get(
        f"/api/canchas/{cancha.pk}/disponibilidad-operativa/",
        {"desde": ayer_semana.isoformat(), "hasta": ayer_semana.isoformat()},
    )
    assert operacion.status_code == 200
    assert operacion.data["bloques"][0]["estado"] == "pasada"
    assert operacion.data["bloques"][0]["habilitada_operativamente"] is False
    cancha.estado = EstadoCancha.INACTIVA
    cancha.save(update_fields=["estado"])
    assert APIClient().get(f"/api/publico/canchas/{cancha.pk}/").status_code == 404
