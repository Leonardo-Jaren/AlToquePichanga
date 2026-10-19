from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.empresas.models import AccesoPlataforma, RolEmpresa
from apps.empresas.repositories.alcance import (
    empresas_administrables,
    membresias_autorizadas,
    membresias_propietario_estado,
)


def consultar_empresas(usuario: User) -> list[dict]:
    empresas = list(empresas_administrables(usuario).values("id", "nombre", "activa"))
    if usuario.is_superuser:
        AccesoPlataforma.objects.create(usuario=usuario, accion="listar_empresas")
    return empresas


def consultar_empresa(usuario: User, identificador: int) -> dict:
    empresa = get_object_or_404(empresas_administrables(usuario), pk=identificador)
    if usuario.is_superuser:
        AccesoPlataforma.objects.create(
            usuario=usuario, empresa=empresa, accion="consultar_empresa"
        )
    return {"id": empresa.id, "nombre": empresa.nombre, "activa": empresa.activa}


def acceso_panel(usuario: User, rol: str) -> dict:
    if rol == "plataforma":
        autorizado = usuario.is_superuser
    elif rol in RolEmpresa.values:
        autorizado = membresias_autorizadas(usuario).filter(rol=rol).exists()
    else:
        autorizado = rol == "jugador"
    if not autorizado:
        raise PermissionDenied("No tienes permisos para este panel.")
    if rol == "plataforma":
        AccesoPlataforma.objects.create(usuario=usuario, accion="acceder_panel")
    return {"rol": rol, "mensaje": "Acceso autorizado. Panel en preparación."}


def acceso_panel_limitado(usuario: User, rol: str) -> dict | None:
    if rol != RolEmpresa.DUENO:
        return None
    empresa = membresias_propietario_estado(usuario).first()
    if not empresa:
        return None
    return {
        "rol": rol,
        "mensaje": "Acceso limitado: consulta el estado de la empresa y su suscripción.",
    }
