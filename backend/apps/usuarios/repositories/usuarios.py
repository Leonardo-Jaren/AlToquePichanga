from django.contrib.auth.models import User

from apps.usuarios.models import PerfilUsuario


def usuario_por_correo(correo: str) -> User | None:
    perfil = PerfilUsuario.objects.select_related("usuario").filter(
        correo__iexact=correo
    ).first()
    return perfil.usuario if perfil else None


def perfil_de(usuario: User) -> PerfilUsuario:
    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    return perfil
