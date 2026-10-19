from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.canchas.models import Cancha, EstadoCancha
from apps.empresas.models import (
    Empresa,
    EstadoEmpresa,
    MembresiaEmpresa,
    RegistroAuditoria,
    RolEmpresa,
)
from apps.horarios.models import ExcepcionHorario
from apps.sedes.models import AsignacionSede, Sede
from apps.suscripciones.models import (
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    PlanSuscripcion,
    SuscripcionEmpresa,
)

pytestmark = pytest.mark.django_db


def _contexto(correo: str = "dueno-horarios@example.com") -> tuple:
    propietario = User.objects.create_user(
        username=correo, email=correo, password="AlToque-test-493!"
    )
    empresa = Empresa.objects.create(
        nombre=f"Empresa {correo}", estado=EstadoEmpresa.ACTIVA, activa=True
    )
    MembresiaEmpresa.objects.create(
        usuario=propietario, empresa=empresa, rol=RolEmpresa.DUENO
    )
    hoy = timezone.localdate()
    plan = PlanSuscripcion.objects.create(
        nombre=f"Plan {correo}", precio=Decimal("20.00"), moneda="PEN",
        frecuencia=FrecuenciaSuscripcion.MENSUAL,
    )
    SuscripcionEmpresa.objects.create(
        empresa=empresa, plan=plan, estado=EstadoSuscripcion.ACTIVA,
        fecha_inicio=hoy - timedelta(days=1), fecha_vencimiento=hoy + timedelta(days=30),
        importe_acordado=plan.precio, moneda_acordada="PEN",
        frecuencia_acordada=FrecuenciaSuscripcion.MENSUAL,
    )
    sede = Sede.objects.create(
        empresa=empresa, nombre="Sede Centro", direccion="Av. Lima 100",
        horario_general={"lunes": ["00:00-23:59"]},
    )
    cancha = Cancha.objects.create(
        sede=sede, nombre="Cancha 1", modalidad=7, tipo_superficie="Sintético"
    )
    api = APIClient()
    api.force_authenticate(propietario)
    return propietario, empresa, sede, cancha, api


def _lunes_futuro() -> date:
    hoy = timezone.localdate()
    dias = (7 - hoy.weekday()) % 7
    return hoy + timedelta(days=dias + 7)


def _hora_iso(fecha: date, hora: str) -> str:
    return f"{fecha.isoformat()}T{hora}:00-05:00"


def _intervalo(dia: int, apertura: str, cierre: str) -> dict:
    return {"dia_semana": dia, "hora_apertura": apertura, "hora_cierre": cierre}


def _crear_excepcion(api: APIClient, sede_id: int, fecha: date, tipo: str, inicio: str, fin: str):
    return api.post("/api/horarios/excepciones/", {
        "sede_id": sede_id,
        "tipo": tipo,
        "fecha_inicio": _hora_iso(fecha, inicio),
        "fecha_fin": _hora_iso(fecha, fin),
        "motivo": "Trabajo de mantenimiento",
    }, format="json")


def test_horario_sede_estructurado_y_ignora_json_heredado():
    propietario, _, sede, _, api = _contexto()

    inicial = api.get(f"/api/sedes/{sede.pk}/horario-semanal/")
    assert inicial.status_code == 200
    assert inicial.data == {
        "sede_id": sede.pk,
        "configurado": False,
        "zona_horaria": "America/Lima",
        "intervalos": [],
    }

    lunes = _lunes_futuro().weekday()
    guardado = api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [
            _intervalo(lunes, "08:00", "12:00"),
            _intervalo(lunes, "14:00", "23:00"),
        ],
    }, format="json")
    assert guardado.status_code == 200, guardado.data
    assert guardado.data["configurado"] is True
    assert len(guardado.data["intervalos"]) == 2
    assert RegistroAuditoria.objects.filter(
        actor=propietario, recurso="horario_sede", accion="actualizar"
    ).count() == 1


def test_rechaza_igualdad_solapes_y_cruce_semanal():
    _, _, sede, _, api = _contexto()
    domingo = 6
    lunes = 0
    casos = [
        [_intervalo(lunes, "08:00", "08:00")],
        [_intervalo(lunes, "08:00", "12:00"), _intervalo(lunes, "11:00", "15:00")],
        [_intervalo(domingo, "23:00", "03:00"), _intervalo(lunes, "02:00", "04:00")],
    ]
    for intervalos in casos:
        respuesta = api.put(
            f"/api/sedes/{sede.pk}/horario-semanal/",
            {"intervalos": intervalos}, format="json",
        )
        assert respuesta.status_code == 400


def test_horario_cancha_parcial_hereda_y_es_subconjunto_de_sede():
    _, _, sede, cancha, api = _contexto()
    horario_sede = [
        _intervalo(dia, "08:00", "23:00") for dia in range(7)
    ]
    assert api.put(
        f"/api/sedes/{sede.pk}/horario-semanal/",
        {"intervalos": horario_sede}, format="json",
    ).status_code == 200

    propios = [_intervalo(dia, "16:00", "23:00") for dia in range(5)]
    guardado = api.put(f"/api/canchas/{cancha.pk}/horario-semanal/", {
        "hereda_horario_sede": False,
        "dias_heredados": [5, 6],
        "intervalos": propios,
    }, format="json")
    assert guardado.status_code == 200, guardado.data
    assert guardado.data["dias_heredados"] == [5, 6]
    assert len(guardado.data["intervalos"]) == 5
    assert len(guardado.data["intervalos_efectivos"]) == 7

    fuera_de_sede = api.put(f"/api/canchas/{cancha.pk}/horario-semanal/", {
        "hereda_horario_sede": False,
        "dias_heredados": [5, 6],
        "intervalos": [_intervalo(0, "07:00", "09:00")],
    }, format="json")
    assert fuera_de_sede.status_code == 400


def test_actualizar_sede_no_invalida_horario_propio_de_cancha():
    _, _, sede, cancha, api = _contexto()
    lunes = _lunes_futuro().weekday()
    assert api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(lunes, "08:00", "23:00")],
    }, format="json").status_code == 200
    assert api.put(f"/api/canchas/{cancha.pk}/horario-semanal/", {
        "hereda_horario_sede": False,
        "intervalos": [_intervalo(lunes, "16:00", "22:00")],
    }, format="json").status_code == 200

    recorte = api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(lunes, "08:00", "18:00")],
    }, format="json")
    assert recorte.status_code == 400


def test_permisos_multiempresa_y_cajero_solo_lectura():
    propietario, empresa, sede, cancha, api = _contexto()
    horario = api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(0, "08:00", "23:00")],
    }, format="json")
    assert horario.status_code == 200

    cajero = User.objects.create_user(username="cajero-horarios", password="x")
    membresia = MembresiaEmpresa.objects.create(
        usuario=cajero, empresa=empresa, rol=RolEmpresa.CAJERO
    )
    AsignacionSede.objects.create(sede=sede, membresia=membresia)
    api_cajero = APIClient()
    api_cajero.force_authenticate(cajero)
    assert api_cajero.get(f"/api/sedes/{sede.pk}/horario-semanal/").status_code == 200
    assert api_cajero.get(f"/api/canchas/{cancha.pk}/horario-semanal/").status_code == 200
    assert api_cajero.put(
        f"/api/sedes/{sede.pk}/horario-semanal/", {"intervalos": []}, format="json"
    ).status_code == 403
    assert api_cajero.post("/api/horarios/excepciones/", {
        "sede_id": sede.pk, "tipo": "cierre",
        "fecha_inicio": _hora_iso(_lunes_futuro(), "09:00"),
        "fecha_fin": _hora_iso(_lunes_futuro(), "10:00"), "motivo": "Evento",
    }, format="json").status_code == 403

    otro, _, otra_sede, _, api_otro = _contexto("otro-dueno-horarios@example.com")
    assert otro.pk != propietario.pk
    assert api_otro.get(f"/api/sedes/{sede.pk}/horario-semanal/").status_code == 404
    assert api_otro.get(f"/api/canchas/{cancha.pk}/horario-semanal/").status_code == 404
    assert otra_sede.pk != sede.pk

    jugador = User.objects.create_user(username="jugador-sin-alcance", password="x")
    api_jugador = APIClient()
    api_jugador.force_authenticate(jugador)
    assert api_jugador.get(f"/api/canchas/{cancha.pk}/disponibilidad-operativa/", {
        "desde": _lunes_futuro().isoformat(), "hasta": _lunes_futuro().isoformat(),
    }).status_code == 404


def test_excepciones_solape_cierre_gana_y_anulacion_conserva_historial():
    propietario, _, sede, cancha, api = _contexto()
    lunes = _lunes_futuro()
    lunes_idx = lunes.weekday()
    assert api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(lunes_idx, "08:00", "11:00")],
    }, format="json").status_code == 200

    cierre = _crear_excepcion(api, sede.pk, lunes, "cierre", "09:00", "10:00")
    assert cierre.status_code == 201, cierre.data
    duplicado = _crear_excepcion(api, sede.pk, lunes, "cierre", "09:30", "10:30")
    assert duplicado.status_code == 400
    ampliacion = _crear_excepcion(api, sede.pk, lunes, "ampliacion", "09:00", "10:00")
    assert ampliacion.status_code == 201, ampliacion.data

    disponibilidad = api.get(
        f"/api/canchas/{cancha.pk}/disponibilidad-operativa/",
        {"desde": lunes.isoformat(), "hasta": lunes.isoformat()},
    )
    assert disponibilidad.status_code == 200, disponibilidad.data
    assert disponibilidad.data["considera_reservas"] is False
    bloques = disponibilidad.data["bloques"]
    assert [item["estado"] for item in bloques] == ["operativa", "cerrada", "operativa"]
    assert all(item["considera_reservas"] is False for item in bloques)
    assert all("libre" not in item["estado"] and "disponible" not in item["estado"] for item in bloques)

    id_cierre = cierre.data["id"]
    anulacion = api.post(
        f"/api/horarios/excepciones/{id_cierre}/anular/", {"confirmar": True}, format="json"
    )
    assert anulacion.status_code == 200
    assert anulacion.data["anulada"] is True
    assert anulacion.data["anulada_por_id"] == propietario.pk
    assert ExcepcionHorario.objects.filter(pk=id_cierre, anulada=True).exists()
    assert api.get("/api/horarios/excepciones/", {
        "sede": sede.pk, "desde": lunes.isoformat(), "hasta": lunes.isoformat(),
    }).data["count"] == 2


def test_excepcion_de_ampliacion_de_cancha_debe_caber_en_sede():
    _, _, sede, cancha, api = _contexto()
    lunes = _lunes_futuro()
    assert api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(lunes.weekday(), "08:00", "23:00")],
    }, format="json").status_code == 200

    afuera = api.post("/api/horarios/excepciones/", {
        "sede_id": sede.pk, "cancha_id": cancha.pk, "tipo": "ampliacion",
        "fecha_inicio": _hora_iso(lunes, "07:00"),
        "fecha_fin": _hora_iso(lunes, "09:00"), "motivo": "Apertura temprana",
    }, format="json")
    assert afuera.status_code == 400
    dentro = api.post("/api/horarios/excepciones/", {
        "sede_id": sede.pk, "cancha_id": cancha.pk, "tipo": "ampliacion",
        "fecha_inicio": _hora_iso(lunes, "08:30"),
        "fecha_fin": _hora_iso(lunes, "09:30"), "motivo": "Evento autorizado",
    }, format="json")
    assert dentro.status_code == 201, dentro.data


def test_disponibilidad_resuelve_cruce_de_medianoche_y_estado_mantenimiento():
    _, _, sede, cancha, api = _contexto()
    lunes = _lunes_futuro()
    assert api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(lunes.weekday(), "22:00", "02:00")],
    }, format="json").status_code == 200
    martes = lunes + timedelta(days=1)
    respuesta = api.get(
        f"/api/canchas/{cancha.pk}/disponibilidad-operativa/",
        {"desde": martes.isoformat(), "hasta": martes.isoformat()},
    )
    assert respuesta.status_code == 200, respuesta.data
    assert [item["fecha_inicio"] for item in respuesta.data["bloques"]] == [
        f"{martes.isoformat()}T00:00:00-05:00",
        f"{martes.isoformat()}T01:00:00-05:00",
    ]

    cancha.estado = EstadoCancha.MANTENIMIENTO
    cancha.save(update_fields=["estado"])
    mantenimiento = api.get(
        f"/api/canchas/{cancha.pk}/disponibilidad-operativa/",
        {"desde": martes.isoformat(), "hasta": martes.isoformat()},
    )
    assert all(item["estado"] == "mantenimiento" for item in mantenimiento.data["bloques"])
    assert not any(item["habilitada_operativamente"] for item in mantenimiento.data["bloques"])


def test_disponibilidad_informa_bloques_pasados_y_cierre_de_sede_a_otras_canchas():
    _, _, sede, cancha, api = _contexto()
    ayer = timezone.localdate() - timedelta(days=1)
    assert api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(ayer.weekday(), "08:00", "10:00")],
    }, format="json").status_code == 200
    pasado = api.get(
        f"/api/canchas/{cancha.pk}/disponibilidad-operativa/",
        {"desde": ayer.isoformat(), "hasta": ayer.isoformat()},
    )
    assert [item["estado"] for item in pasado.data["bloques"]] == ["pasada", "pasada"]
    assert not any(item["habilitada_operativamente"] for item in pasado.data["bloques"])

    lunes = _lunes_futuro()
    otra_cancha = Cancha.objects.create(
        sede=sede, nombre="Cancha 2", modalidad=7, tipo_superficie="Sintético"
    )
    assert api.put(f"/api/sedes/{sede.pk}/horario-semanal/", {
        "intervalos": [_intervalo(lunes.weekday(), "08:00", "11:00")],
    }, format="json").status_code == 200
    cierre = _crear_excepcion(api, sede.pk, lunes, "cierre", "09:00", "10:00")
    assert cierre.status_code == 201

    afectada = api.get(
        f"/api/canchas/{otra_cancha.pk}/disponibilidad-operativa/",
        {"desde": lunes.isoformat(), "hasta": lunes.isoformat()},
    )
    assert [item["estado"] for item in afectada.data["bloques"]] == [
        "operativa", "cerrada", "operativa"
    ]


def test_disponibilidad_limita_rango_inclusivo_a_31_dias():
    _, _, _, cancha, api = _contexto()
    desde = _lunes_futuro()
    respuesta = api.get(
        f"/api/canchas/{cancha.pk}/disponibilidad-operativa/",
        {"desde": desde.isoformat(), "hasta": (desde + timedelta(days=31)).isoformat()},
    )
    assert respuesta.status_code == 400
