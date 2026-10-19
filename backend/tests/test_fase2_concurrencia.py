from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import close_old_connections, connection
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.empresas.models import Empresa, EstadoEmpresa, MembresiaEmpresa, RolEmpresa
from apps.empresas.services.personal import invitar_personal
from apps.sedes.models import Sede
from apps.sedes.services.sedes import crear_sede
from apps.suscripciones.models import (
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    PlanSuscripcion,
    SuscripcionEmpresa,
)
from apps.usuarios.models import PerfilUsuario

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.skipif(connection.vendor != "postgresql", reason="Requiere PostgreSQL y row locks."),
]


def test_dos_creaciones_simultaneas_respetan_el_limite_de_sedes():
    propietario = User.objects.create_user(
        username="concurrencia@example.com", email="concurrencia@example.com",
    )
    PerfilUsuario.objects.create(usuario=propietario, correo=propietario.email)
    empresa = Empresa.objects.create(
        nombre="Concurrencia", razon_social="Concurrencia", activa=True,
        estado=EstadoEmpresa.ACTIVA,
    )
    MembresiaEmpresa.objects.create(
        usuario=propietario, empresa=empresa, rol=RolEmpresa.DUENO,
    )
    plan = PlanSuscripcion.objects.create(
        nombre="Un solo complejo", precio=Decimal("10.00"), moneda="PEN",
        frecuencia=FrecuenciaSuscripcion.MENSUAL, maximo_sedes=1,
    )
    hoy = timezone.localdate()
    SuscripcionEmpresa.objects.create(
        empresa=empresa, plan=plan, estado=EstadoSuscripcion.ACTIVA,
        fecha_inicio=hoy, fecha_vencimiento=hoy, importe_acordado=Decimal("10.00"),
        moneda_acordada="PEN", frecuencia_acordada=FrecuenciaSuscripcion.MENSUAL,
    )

    def intentar_crear(nombre: str) -> bool:
        close_old_connections()
        try:
            usuario = User.objects.get(pk=propietario.pk)
            crear_sede(usuario, {
                "empresa_id": empresa.pk, "nombre": nombre, "direccion": "Av. Lima 1",
            })
            return True
        except ValidationError:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as grupo:
        resultados = list(grupo.map(intentar_crear, ["Sede A", "Sede B"]))

    assert sorted(resultados) == [False, True]
    assert Sede.objects.filter(empresa=empresa, activa=True).count() == 1


def test_dos_invitaciones_simultaneas_respetan_el_limite_de_empleados():
    propietario = User.objects.create_user(
        username="equipo-concurrente@example.com", email="equipo-concurrente@example.com",
    )
    PerfilUsuario.objects.create(usuario=propietario, correo=propietario.email)
    empresa = Empresa.objects.create(
        nombre="Equipo concurrente", razon_social="Equipo concurrente", activa=True,
        estado=EstadoEmpresa.ACTIVA,
    )
    MembresiaEmpresa.objects.create(
        usuario=propietario, empresa=empresa, rol=RolEmpresa.DUENO,
    )
    plan = PlanSuscripcion.objects.create(
        nombre="Un solo empleado", precio=Decimal("10.00"), moneda="PEN",
        frecuencia=FrecuenciaSuscripcion.MENSUAL, maximo_empleados=1,
    )
    hoy = timezone.localdate()
    SuscripcionEmpresa.objects.create(
        empresa=empresa, plan=plan, estado=EstadoSuscripcion.ACTIVA,
        fecha_inicio=hoy, fecha_vencimiento=hoy, importe_acordado=Decimal("10.00"),
        moneda_acordada="PEN", frecuencia_acordada=FrecuenciaSuscripcion.MENSUAL,
    )
    sede = Sede.objects.create(empresa=empresa, nombre="Centro", direccion="Av. Lima 1")

    def intentar_invitar(correo: str) -> bool:
        close_old_connections()
        try:
            usuario = User.objects.get(pk=propietario.pk)
            invitar_personal(usuario, empresa.pk, {
                "correo": correo, "rol": RolEmpresa.CAJERO, "sedes": [sede.pk],
            })
            return True
        except ValidationError:
            return False
        finally:
            close_old_connections()

    correos = ["cajero-a@example.com", "cajero-b@example.com"]
    with ThreadPoolExecutor(max_workers=2) as grupo:
        resultados = list(grupo.map(intentar_invitar, correos))

    assert sorted(resultados) == [False, True]
    assert empresa.invitaciones.filter(aceptada_en__isnull=True, cancelada_en__isnull=True).count() == 1
