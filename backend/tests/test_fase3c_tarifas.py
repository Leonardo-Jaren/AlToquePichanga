from datetime import date, datetime, time, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.canchas.models import Cancha
from apps.empresas.models import (
    AccesoPlataforma,
    Empresa,
    EstadoEmpresa,
    MembresiaEmpresa,
    RegistroAuditoria,
    RolEmpresa,
)
from apps.horarios.models import (
    ExcepcionHorario,
    HorarioSede,
    IntervaloHorarioSede,
    TipoExcepcionHorario,
)
from apps.sedes.models import AsignacionSede, Sede
from apps.suscripciones.models import (
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    PlanSuscripcion,
    SuscripcionEmpresa,
)
from apps.tarifas.models import ReglaTarifa

pytestmark = pytest.mark.django_db


def _contexto(correo: str = "dueno-tarifas@example.test") -> tuple:
    usuario = User.objects.create_user(username=correo, email=correo, password="AlToque-test-493!")
    empresa = Empresa.objects.create(nombre=f"Empresa {correo}", estado=EstadoEmpresa.ACTIVA)
    MembresiaEmpresa.objects.create(usuario=usuario, empresa=empresa, rol=RolEmpresa.DUENO)
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
    sede = Sede.objects.create(empresa=empresa, nombre="Sede Centro", direccion="Av. Lima 100")
    cancha = Cancha.objects.create(
        sede=sede, nombre="Cancha 1", modalidad=7, tipo_superficie="Sintético",
    )
    api = APIClient()
    api.force_authenticate(usuario)
    return usuario, empresa, sede, cancha, api


def _proximo_dia(dia: int) -> date:
    hoy = timezone.localdate()
    diferencia = (dia - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=diferencia)


def _regla(
    precio: str = "50.00", *, tipo: str = "diurna", dias: list[int] | None = None,
    inicio: str = "18:00", fin: str = "23:00", **cambios,
) -> dict:
    datos = {
        "tipo": tipo,
        "dias_semana": list(range(5)) if dias is None and tipo in {"diurna", "nocturna"} else (dias or []),
        "hora_inicio": inicio,
        "hora_fin": fin,
        "todo_el_dia": False,
        "vigente_desde": timezone.localdate().isoformat(),
        "precio_hora": precio,
        "moneda": "PEN",
    }
    datos.update(cambios)
    return datos


def _horario(sede: Sede, dia: int, apertura: str, cierre: str) -> None:
    horario, _ = HorarioSede.objects.get_or_create(
        sede=sede, defaults={"configurado": True},
    )
    IntervaloHorarioSede.objects.create(
        horario=horario,
        dia_semana=dia,
        hora_apertura=time.fromisoformat(apertura),
        hora_cierre=time.fromisoformat(cierre),
    )


def test_registro_edicion_desactivacion_y_auditoria_de_tarifa():
    usuario, empresa, _, cancha, api = _contexto()
    creada = api.post(
        f"/api/canchas/{cancha.pk}/tarifas/", _regla(), format="json"
    )
    assert creada.status_code == 201, creada.data
    assert creada.data["precio_hora"] == "50.00"

    editada = api.patch(
        f"/api/canchas/{cancha.pk}/tarifas/{creada.data['id']}/",
        {"precio_hora": "52.35"}, format="json",
    )
    assert editada.status_code == 200, editada.data
    assert editada.data["precio_hora"] == "52.35"

    desactivada = api.post(
        f"/api/canchas/{cancha.pk}/tarifas/{creada.data['id']}/estado/",
        {"activa": False, "confirmar": True}, format="json",
    )
    assert desactivada.status_code == 200
    assert desactivada.data["activa"] is False
    assert RegistroAuditoria.objects.filter(
        actor=usuario, empresa=empresa, recurso="tarifa",
    ).count() == 3
    assert ReglaTarifa.objects.filter(pk=creada.data["id"]).exists()


def test_rechaza_importes_fechas_y_reglas_incompletas():
    _, _, _, cancha, api = _contexto()
    casos = [
        _regla("0.00"),
        _regla("-1.00"),
        _regla(dias=[]),
        _regla(vigente_hasta=(timezone.localdate() - timedelta(days=1)).isoformat()),
        _regla(empresa_id=999),
    ]
    for datos in casos:
        respuesta = api.post(f"/api/canchas/{cancha.pk}/tarifas/", datos, format="json")
        assert respuesta.status_code == 400, respuesta.data
    assert ReglaTarifa.objects.count() == 0


def test_rechaza_reglas_ambiguas_al_crear_y_editar():
    _, _, _, cancha, api = _contexto()
    primera = api.post(
        f"/api/canchas/{cancha.pk}/tarifas/",
        _regla(inicio="16:00", fin="19:00"), format="json",
    )
    assert primera.status_code == 201, primera.data
    segunda = api.post(
        f"/api/canchas/{cancha.pk}/tarifas/",
        _regla("70.00", inicio="19:00", fin="21:00"), format="json",
    )
    assert segunda.status_code == 201, segunda.data
    solapada = api.post(
        f"/api/canchas/{cancha.pk}/tarifas/",
        _regla("75.00", inicio="18:00", fin="21:00"), format="json",
    )
    assert solapada.status_code == 400
    edicion = api.patch(
        f"/api/canchas/{cancha.pk}/tarifas/{primera.data['id']}/",
        {"hora_fin": "20:00"}, format="json",
    )
    assert edicion.status_code == 400
    assert ReglaTarifa.objects.get(pk=primera.data["id"]).hora_inicio == time(16)


def test_prioridad_fin_de_semana_feriado_y_fecha_especial():
    _, _, _, cancha, api = _contexto()
    sabado = _proximo_dia(5)
    lunes = _proximo_dia(0)
    reglas = [
        _regla("40.00", dias=list(range(7)), inicio="09:00", fin="18:00"),
        _regla("80.00", tipo="fin_semana", inicio="09:00", fin="18:00"),
        _regla(
            "100.00", tipo="feriado", inicio="09:00", fin="18:00",
            fecha_aplicable_desde=lunes.isoformat(), fecha_aplicable_hasta=lunes.isoformat(),
        ),
        _regla(
            "120.00", tipo="especial", inicio="09:00", fin="18:00",
            fecha_aplicable_desde=lunes.isoformat(), fecha_aplicable_hasta=lunes.isoformat(),
        ),
    ]
    for datos in reglas:
        respuesta = api.post(f"/api/canchas/{cancha.pk}/tarifas/", datos, format="json")
        assert respuesta.status_code == 201, respuesta.data

    _horario(cancha.sede, sabado.weekday(), "09:00", "18:00")
    disponibilidad = api.get(f"/api/canchas/{cancha.pk}/disponibilidad-operativa/", {
        "desde": sabado.isoformat(), "hasta": sabado.isoformat(),
    })
    assert disponibilidad.status_code == 200
    assert disponibilidad.data["considera_reservas"] is False
    sabado_09 = next(b for b in disponibilidad.data["bloques"] if b["fecha_inicio"].endswith("09:00:00-05:00"))
    assert sabado_09["precio"] == "80.00"
    assert sabado_09["tipo_tarifa"] == "fin_semana"

    _horario(cancha.sede, lunes.weekday(), "09:00", "18:00")
    lunes_data = api.get(f"/api/canchas/{cancha.pk}/disponibilidad-operativa/", {
        "desde": lunes.isoformat(), "hasta": lunes.isoformat(),
    })
    lunes_09 = next(b for b in lunes_data.data["bloques"] if b["fecha_inicio"].endswith("09:00:00-05:00"))
    assert lunes_09["precio"] == "120.00"
    assert lunes_09["tipo_tarifa"] == "especial"


def test_calculo_varias_horas_por_bloque_y_precision_decimal():
    _, _, sede, cancha, api = _contexto()
    lunes = _proximo_dia(0)
    _horario(sede, lunes.weekday(), "18:00", "23:00")
    for datos in (
        _regla("50.10", dias=[lunes.weekday()], inicio="18:00", fin="19:00"),
        _regla("69.95", tipo="nocturna", dias=[lunes.weekday()], inicio="19:00", fin="23:00"),
    ):
        respuesta = api.post(f"/api/canchas/{cancha.pk}/tarifas/", datos, format="json")
        assert respuesta.status_code == 201, respuesta.data

    calculo = api.post(f"/api/canchas/{cancha.pk}/calcular-precio/", {
        "fecha": lunes.isoformat(), "hora_inicio": "18:00", "duracion_horas": 3,
    }, format="json")
    assert calculo.status_code == 200, calculo.data
    assert [bloque["precio"] for bloque in calculo.data["bloques"]] == [
        "50.10", "69.95", "69.95",
    ]
    assert calculo.data["subtotal"] == calculo.data["total"] == "190.00"
    assert calculo.data["moneda"] == "PEN"


def test_calculo_cruza_medianoche_y_sigue_el_dia_de_inicio_de_la_regla():
    _, _, sede, cancha, api = _contexto()
    lunes = _proximo_dia(0)
    _horario(sede, lunes.weekday(), "22:00", "02:00")
    tarifa = api.post(f"/api/canchas/{cancha.pk}/tarifas/", _regla(
        "33.33", tipo="nocturna", dias=[lunes.weekday()], inicio="21:00", fin="03:00",
    ), format="json")
    assert tarifa.status_code == 201, tarifa.data

    calculo = api.post(f"/api/canchas/{cancha.pk}/calcular-precio/", {
        "fecha": lunes.isoformat(), "hora_inicio": "23:00", "duracion_horas": 2,
    }, format="json")
    assert calculo.status_code == 200, calculo.data
    assert [bloque["fecha_inicio"][:16] for bloque in calculo.data["bloques"]] == [
        f"{lunes.isoformat()}T23:00", f"{(lunes + timedelta(days=1)).isoformat()}T00:00",
    ]
    assert calculo.data["total"] == "66.66"


def test_tarifa_faltante_y_bloque_cerrado_no_se_cotizan():
    propietario, _, sede, cancha, api = _contexto()
    lunes = _proximo_dia(0)
    _horario(sede, lunes.weekday(), "18:00", "21:00")
    sin_tarifa = api.get(f"/api/canchas/{cancha.pk}/disponibilidad-operativa/", {
        "desde": lunes.isoformat(), "hasta": lunes.isoformat(),
    })
    abierto = next(b for b in sin_tarifa.data["bloques"] if b["fecha_inicio"].endswith("18:00:00-05:00"))
    assert abierto["tarifa_estado"] == "sin_configurar"
    assert abierto["precio"] is None
    calculo_sin_tarifa = api.post(f"/api/canchas/{cancha.pk}/calcular-precio/", {
        "fecha": lunes.isoformat(), "hora_inicio": "18:00", "duracion_horas": 1,
    }, format="json")
    assert calculo_sin_tarifa.status_code == 400

    inicio = timezone.make_aware(datetime.combine(lunes, time(18)), timezone.get_current_timezone())
    ExcepcionHorario.objects.create(
        sede=sede, cancha=cancha, tipo=TipoExcepcionHorario.CIERRE,
        fecha_inicio=inicio, fecha_fin=inicio + timedelta(hours=1),
        motivo="Mantenimiento de prueba", creado_por=propietario,
    )
    api.post(f"/api/canchas/{cancha.pk}/tarifas/", _regla(
        "40.00", dias=[lunes.weekday()], inicio="18:00", fin="21:00",
    ), format="json")
    cerrada = api.get(f"/api/canchas/{cancha.pk}/disponibilidad-operativa/", {
        "desde": lunes.isoformat(), "hasta": lunes.isoformat(),
    })
    bloque_cerrado = next(b for b in cerrada.data["bloques"] if b["fecha_inicio"].endswith("18:00:00-05:00"))
    assert bloque_cerrado["estado"] == "cerrada"
    assert bloque_cerrado["precio"] is None
    calculo_cerrado = api.post(f"/api/canchas/{cancha.pk}/calcular-precio/", {
        "fecha": lunes.isoformat(), "hora_inicio": "18:00", "duracion_horas": 1,
    }, format="json")
    assert calculo_cerrado.status_code == 400


def test_permisos_multiempresa_cajero_admin_de_sede_y_superadministrador():
    _, empresa, sede, cancha, api = _contexto()
    regla = api.post(
        f"/api/canchas/{cancha.pk}/tarifas/", _regla(), format="json"
    )
    assert regla.status_code == 201

    admin = User.objects.create_user(username="admin-tarifas", password="x")
    membresia_admin = MembresiaEmpresa.objects.create(
        usuario=admin, empresa=empresa, rol=RolEmpresa.ADMINISTRADOR_SEDE,
    )
    AsignacionSede.objects.create(sede=sede, membresia=membresia_admin)
    otra_sede = Sede.objects.create(empresa=empresa, nombre="Sede No Asignada", direccion="Av. Perú 10")
    otra_cancha_empresa = Cancha.objects.create(
        sede=otra_sede, nombre="Cancha No Asignada", modalidad=7, tipo_superficie="Sintético",
    )
    api_admin = APIClient()
    api_admin.force_authenticate(admin)
    assert api_admin.get(f"/api/canchas/{cancha.pk}/tarifas/").status_code == 200
    assert api_admin.get(f"/api/canchas/{otra_cancha_empresa.pk}/tarifas/").status_code == 404
    assert api_admin.post(
        f"/api/canchas/{cancha.pk}/tarifas/", _regla("60.00", inicio="10:00", fin="12:00"),
        format="json",
    ).status_code == 201

    cajero = User.objects.create_user(username="cajero-tarifas", password="x")
    membresia_cajero = MembresiaEmpresa.objects.create(
        usuario=cajero, empresa=empresa, rol=RolEmpresa.CAJERO,
    )
    AsignacionSede.objects.create(sede=sede, membresia=membresia_cajero)
    api_cajero = APIClient()
    api_cajero.force_authenticate(cajero)
    assert api_cajero.get(f"/api/canchas/{cancha.pk}/tarifas/").status_code == 200
    assert api_cajero.patch(
        f"/api/canchas/{cancha.pk}/tarifas/{regla.data['id']}/",
        {"precio_hora": "80.00"}, format="json",
    ).status_code == 403

    _, _, _, otra_cancha, otra_api = _contexto("otro-dueno-tarifas@example.test")
    assert otra_api.get(f"/api/canchas/{cancha.pk}/tarifas/").status_code == 404
    assert otra_api.patch(
        f"/api/canchas/{cancha.pk}/tarifas/{regla.data['id']}/",
        {"precio_hora": "90.00"}, format="json",
    ).status_code == 404
    assert otra_cancha.pk != cancha.pk

    superadmin = User.objects.create_superuser(
        username="superadmin-tarifas", email="superadmin-tarifas@example.test", password="x",
    )
    api_global = APIClient()
    api_global.force_authenticate(superadmin)
    assert api_global.get(f"/api/canchas/{cancha.pk}/tarifas/").status_code == 200
    assert api_global.get(f"/api/canchas/{otra_cancha_empresa.pk}/tarifas/").status_code == 200
    tarifa_global = api_global.post(
        f"/api/canchas/{otra_cancha_empresa.pk}/tarifas/",
        _regla("90.00", tipo="fin_semana", inicio="09:00", fin="11:00"), format="json",
    )
    assert tarifa_global.status_code == 201, tarifa_global.data
    assert AccesoPlataforma.objects.filter(
        usuario=superadmin, accion="consultar_tarifas_cancha",
    ).exists()
