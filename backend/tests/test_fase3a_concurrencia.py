from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.db import close_old_connections, connection
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.canchas.models import Cancha, EstadoCancha
from apps.canchas.services.canchas import crear_cancha
from apps.empresas.models import Empresa, EstadoEmpresa, MembresiaEmpresa, RolEmpresa
from apps.sedes.models import Sede
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


def test_dos_creaciones_simultaneas_respetan_el_limite_de_canchas():
    propietario = User.objects.create_user(
        username="concurrencia-canchas@example.com",
        email="concurrencia-canchas@example.com",
    )
    PerfilUsuario.objects.create(usuario=propietario, correo=propietario.email)
    empresa = Empresa.objects.create(
        nombre="Empresa Concurrente", activa=True, estado=EstadoEmpresa.ACTIVA
    )
    MembresiaEmpresa.objects.create(
        usuario=propietario, empresa=empresa, rol=RolEmpresa.DUENO
    )
    plan = PlanSuscripcion.objects.create(
        nombre="Una cancha concurrente", precio=Decimal("10.00"), moneda="PEN",
        frecuencia=FrecuenciaSuscripcion.MENSUAL, maximo_canchas=1,
    )
    hoy = timezone.localdate()
    SuscripcionEmpresa.objects.create(
        empresa=empresa, plan=plan, estado=EstadoSuscripcion.ACTIVA,
        fecha_inicio=hoy, fecha_vencimiento=hoy, importe_acordado=plan.precio,
        moneda_acordada="PEN", frecuencia_acordada=FrecuenciaSuscripcion.MENSUAL,
    )
    sedes = [
        Sede.objects.create(empresa=empresa, nombre=f"Sede {indice}", direccion="Av. Lima 1")
        for indice in range(2)
    ]

    def intentar_crear(sede_pk: int) -> bool:
        close_old_connections()
        try:
            usuario = User.objects.get(pk=propietario.pk)
            crear_cancha(usuario, {
                "sede_id": sede_pk, "nombre": f"Cancha {sede_pk}",
                "modalidad": 7, "tipo_superficie": "Sintético",
            })
            return True
        except ValidationError:
            return False
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as grupo:
        resultados = list(grupo.map(intentar_crear, [s.pk for s in sedes]))

    assert sorted(resultados) == [False, True]
    assert Cancha.objects.filter(
        sede__empresa=empresa,
        estado__in=[EstadoCancha.ACTIVA, EstadoCancha.MANTENIMIENTO],
    ).count() == 1
