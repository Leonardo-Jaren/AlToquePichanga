from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient

from apps.empresas.models import Empresa, EstadoEmpresa, MembresiaEmpresa, RolEmpresa
from apps.suscripciones.models import (
    ConfiguracionSuscripcion,
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    PeriodoSuscripcion,
    PlanSuscripcion,
    SuscripcionEmpresa,
)
from apps.suscripciones.services.reglas import suscripcion_operativa
from apps.usuarios.models import PerfilUsuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def crear_usuario():
    def crear(correo: str, *, superusuario: bool = False) -> User:
        usuario = User.objects.create_user(
            username=correo, email=correo, password="Pichanga-fuerte-927!",
            is_superuser=superusuario, is_staff=superusuario,
        )
        PerfilUsuario.objects.create(usuario=usuario, correo=correo)
        return usuario

    return crear


def cliente(usuario: User) -> APIClient:
    api = APIClient()
    api.force_authenticate(usuario)
    return api


def crear_empresa(usuario: User, nombre: str) -> Empresa:
    empresa = Empresa.objects.create(
        nombre=nombre, razon_social=nombre, estado=EstadoEmpresa.ACTIVA, activa=True,
    )
    MembresiaEmpresa.objects.create(usuario=usuario, empresa=empresa, rol=RolEmpresa.DUENO)
    return empresa


def crear_plan(**cambios) -> PlanSuscripcion:
    datos = {
        "nombre": "Plan de prueba", "precio": Decimal("120.00"), "moneda": "PEN",
        "frecuencia": FrecuenciaSuscripcion.MENSUAL, "maximo_sedes": None,
        "maximo_empleados": None,
    }
    datos.update(cambios)
    return PlanSuscripcion.objects.create(**datos)


def activar_suscripcion(empresa: Empresa, plan: PlanSuscripcion) -> SuscripcionEmpresa:
    hoy = timezone.localdate()
    return SuscripcionEmpresa.objects.create(
        empresa=empresa, plan=plan, estado=EstadoSuscripcion.ACTIVA,
        fecha_inicio=hoy, fecha_vencimiento=hoy + timedelta(days=30),
        importe_acordado=plan.precio, moneda_acordada=plan.moneda,
        frecuencia_acordada=plan.frecuencia,
    )


def test_renovacion_reactiva_suscripcion_y_empieza_tras_el_periodo_actual(crear_usuario):
    dueno = crear_usuario("renovacion-owner@example.com")
    superadmin = crear_usuario("renovacion-admin@example.com", superusuario=True)
    empresa = crear_empresa(dueno, "Renovación")
    plan = crear_plan(nombre="Base", precio=Decimal("100.00"))
    suscripcion = activar_suscripcion(empresa, plan)
    PeriodoSuscripcion.objects.create(
        suscripcion=suscripcion, plan=plan, fecha_inicio=suscripcion.fecha_inicio,
        fecha_vencimiento=suscripcion.fecha_vencimiento, importe_acordado=Decimal("100.00"),
        moneda_acordada="PEN", frecuencia_acordada=FrecuenciaSuscripcion.MENSUAL,
        creado_por=superadmin,
    )
    api_super = cliente(superadmin)
    assert api_super.post(
        f"/api/plataforma/empresas/{empresa.pk}/suscripcion/estado/",
        {"estado": "suspendida"}, format="json",
    ).status_code == 200
    api_super.patch(f"/api/plataforma/planes/{plan.pk}/", {"precio": "160.00"}, format="json")

    solicitud = cliente(dueno).post(
        f"/api/empresas/administradas/{empresa.pk}/suscripcion/",
        {"plan_id": plan.pk}, format="json",
    )
    assert solicitud.status_code == 201
    assert solicitud.data["tipo"] == "renovacion"
    inicio = suscripcion.fecha_vencimiento + timedelta(days=1)
    aprobacion = api_super.post(
        f"/api/plataforma/solicitudes/{solicitud.data['id']}/resolver/",
        {"aprobar": True, "importe_verificado": "160.00", "fecha_inicio": inicio.isoformat()},
        format="json",
    )

    assert aprobacion.status_code == 200
    periodos = list(PeriodoSuscripcion.objects.order_by("fecha_inicio", "id"))
    assert len(periodos) == 2
    assert periodos[0].importe_acordado == Decimal("100.00")
    assert periodos[1].importe_acordado == Decimal("160.00")
    assert periodos[1].fecha_inicio == inicio
    suscripcion.refresh_from_db()
    assert suscripcion.estado == EstadoSuscripcion.ACTIVA


def test_estado_efectivo_y_gracia_de_suscripcion_configurable(crear_usuario):
    usuario = crear_usuario("gracia@example.com")
    superadmin = crear_usuario("gracia-admin@example.com", superusuario=True)
    empresa = crear_empresa(usuario, "Vigencia")
    plan = crear_plan()
    suscripcion = activar_suscripcion(empresa, plan)
    ConfiguracionSuscripcion.objects.create(dias_gracia=2, actualizado_por=superadmin)
    hoy = suscripcion.fecha_vencimiento + timedelta(days=1)
    suscripcion.fecha_vencimiento = hoy - timedelta(days=1)
    suscripcion.save(update_fields=["fecha_vencimiento"])

    assert suscripcion_operativa(empresa, hoy=hoy)
    assert suscripcion_operativa(empresa, hoy=hoy + timedelta(days=1))
    assert not suscripcion_operativa(empresa, hoy=hoy + timedelta(days=2))


def test_lista_global_muestra_vencimiento_calculado(crear_usuario):
    usuario = crear_usuario("empresa-vencida@example.com")
    superadmin = crear_usuario("super-vigencia@example.com", superusuario=True)
    empresa = crear_empresa(usuario, "Suscripción vencida")
    suscripcion = activar_suscripcion(empresa, crear_plan())
    suscripcion.fecha_vencimiento = timezone.localdate() - timedelta(days=1)
    suscripcion.save(update_fields=["fecha_vencimiento"])

    respuesta = cliente(superadmin).get("/api/empresas/plataforma/")

    assert respuesta.status_code == 200
    fila = next(item for item in respuesta.data["results"] if item["id"] == empresa.pk)
    assert fila["suscripcion"]["estado"] == EstadoSuscripcion.VENCIDA
