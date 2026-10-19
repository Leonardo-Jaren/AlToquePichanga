import pytest
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.http import Http404
from rest_framework.exceptions import PermissionDenied

from apps.empresas.models import AccesoPlataforma, Empresa, MembresiaEmpresa, RolEmpresa
from apps.empresas.services.acceso import (
    acceso_panel,
    consultar_empresa,
    consultar_empresas,
)
from apps.usuarios.models import PerfilUsuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def escenario():
    usuario = User.objects.create_user(username="dueno", email="dueno@example.com")
    propia = Empresa.objects.create(nombre="Empresa A")
    ajena = Empresa.objects.create(nombre="Empresa B")
    MembresiaEmpresa.objects.create(usuario=usuario, empresa=propia, rol=RolEmpresa.DUENO)
    return usuario, propia, ajena


def test_aislamiento_y_jugador_con_varios_roles(escenario):
    usuario, propia, ajena = escenario
    MembresiaEmpresa.objects.create(usuario=usuario, empresa=ajena, rol=RolEmpresa.CAJERO)
    assert consultar_empresa(usuario, propia.id)["id"] == propia.id
    assert len(consultar_empresas(usuario)) == 1
    with pytest.raises(Http404):
        consultar_empresa(usuario, ajena.id)
    assert acceso_panel(usuario, "jugador")["rol"] == "jugador"
    assert acceso_panel(usuario, "cajero")["rol"] == "cajero"


def test_privilegio_global_explicito_y_auditado(escenario):
    usuario, _propia, ajena = escenario
    usuario.is_staff = True
    usuario.save()
    with pytest.raises(PermissionDenied):
        acceso_panel(usuario, "plataforma")
    usuario.is_superuser = True
    usuario.save()
    assert len(consultar_empresas(usuario)) == 2
    assert consultar_empresa(usuario, ajena.id)["id"] == ajena.id
    assert AccesoPlataforma.objects.filter(usuario=usuario).count() == 2


def test_membresia_inactiva_o_empresa_inactiva_no_autoriza(escenario):
    usuario, propia, _ = escenario
    propia.activa = False
    propia.save()
    assert consultar_empresas(usuario) == []
    with pytest.raises(PermissionDenied):
        acceso_panel(usuario, "dueno")


def test_rol_duplicado_o_invalido_rechazado(escenario):
    usuario, propia, _ = escenario
    for rol in [RolEmpresa.DUENO, "superadministrador"]:
        with pytest.raises(IntegrityError), transaction.atomic():
            MembresiaEmpresa.objects.create(usuario=usuario, empresa=propia, rol=rol)


def test_correo_unico_sin_importar_mayusculas():
    uno = User.objects.create_user(username="uno")
    dos = User.objects.create_user(username="dos")
    PerfilUsuario.objects.create(usuario=uno, correo="correo@example.com")
    with pytest.raises(IntegrityError), transaction.atomic():
        PerfilUsuario.objects.create(usuario=dos, correo="CORREO@example.com")
