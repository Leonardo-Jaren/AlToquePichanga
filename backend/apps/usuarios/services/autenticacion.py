from uuid import uuid4

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.exceptions import ValidationError as ErrorEntrada

from apps.usuarios.models import PerfilUsuario
from apps.usuarios.repositories.usuarios import usuario_por_correo
from apps.usuarios.services.correos import encolar_enlace, usuario_del_token
from apps.usuarios.services.perfil import datos_usuario


def validar_contrasena(contrasena: str, usuario: User) -> None:
    try:
        validate_password(contrasena, usuario)
    except ValidationError as exc:
        raise ErrorEntrada({"contrasena": exc.messages}) from None


def registrar(request, datos: dict) -> dict:
    usuario = User(username=uuid4().hex, email=datos["correo"],
                   first_name=datos["nombre"], last_name=datos.get("apellidos", ""))
    validar_contrasena(datos["contrasena"], usuario)
    usuario.set_password(datos["contrasena"])
    try:
        with transaction.atomic():
            usuario.save()
            PerfilUsuario.objects.create(usuario=usuario, correo=datos["correo"])
            if datos.get("invitacion"):
                from apps.empresas.services.personal import aceptar_invitacion

                aceptar_invitacion(usuario, datos["invitacion"])
            encolar_enlace(usuario, verificar=True)
    except IntegrityError:
        raise ErrorEntrada({"correo": ["No se pudo registrar este correo."]}) from None
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
    return datos_usuario(usuario)


def iniciar_sesion(request, datos: dict) -> dict:
    candidato = usuario_por_correo(datos["correo"])
    usuario = authenticate(
        request, username=candidato.username if candidato else "",
        password=datos["contrasena"],
    )
    if usuario is None:
        raise AuthenticationFailed("Correo o contraseña incorrectos.")
    request.session.cycle_key()
    login(request, usuario)
    return datos_usuario(usuario)


def cerrar_sesion(request) -> None:
    logout(request)


def restablecer(datos: dict) -> None:
    with transaction.atomic():
        usuario = usuario_del_token(datos["uid"], datos["token"])
        usuario = User.objects.select_for_update().get(pk=usuario.pk)
        # Revalidar después del bloqueo impide reutilización simultánea.
        usuario_del_token(datos["uid"], datos["token"])
        validar_contrasena(datos["contrasena"], usuario)
        usuario.set_password(datos["contrasena"])
        usuario.save(update_fields=["password"])


def verificar_correo(datos: dict) -> None:
    with transaction.atomic():
        usuario = usuario_del_token(datos["uid"], datos["token"], verificar=True)
        perfil = PerfilUsuario.objects.select_for_update().get(usuario=usuario)
        usuario_del_token(datos["uid"], datos["token"], verificar=True)
        perfil.correo_verificado = True
        perfil.save(update_fields=["correo_verificado"])
