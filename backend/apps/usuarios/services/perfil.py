from django.contrib.auth.models import User
from django.db import transaction

from apps.empresas.repositories.alcance import (
    membresias_autorizadas,
    membresias_propietario_estado,
)
from apps.usuarios.repositories.usuarios import perfil_de


def datos_usuario(usuario: User) -> dict:
    perfil = perfil_de(usuario)
    membresias = [
        {"empresa_id": m.empresa_id, "empresa_nombre": m.empresa.nombre, "rol": m.rol}
        for m in membresias_autorizadas(usuario)
    ]
    ids = {m["empresa_id"] for m in membresias}
    membresias.extend(
        {"empresa_id": m.empresa_id, "empresa_nombre": m.empresa.nombre,
         "rol": m.rol, "acceso_limitado": True}
        for m in membresias_propietario_estado(usuario) if m.empresa_id not in ids
    )
    return {
        "id": usuario.pk,
        "correo": perfil.correo or "",
        "nombre": usuario.first_name,
        "apellidos": usuario.last_name,
        "correo_verificado": perfil.correo_verificado,
        "es_superadministrador": usuario.is_superuser,
        "es_jugador": True,
        "membresias": membresias,
    }


@transaction.atomic
def actualizar_perfil(usuario: User, datos: dict) -> dict:
    usuario.first_name = datos["nombre"]
    usuario.last_name = datos.get("apellidos", usuario.last_name)
    usuario.save(update_fields=["first_name", "last_name"])
    return datos_usuario(usuario)
