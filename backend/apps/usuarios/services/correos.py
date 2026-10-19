from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import (
    PasswordResetTokenGenerator,
    default_token_generator,
)
from django.core.exceptions import ValidationError
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import ValidationError as ErrorEntrada

from apps.usuarios.models import CorreoPendiente
from apps.usuarios.repositories.usuarios import perfil_de, usuario_por_correo


class TokenVerificacion(PasswordResetTokenGenerator):
    key_salt = "altoque.verificacion.correo"

    def _make_hash_value(self, user, timestamp):
        perfil = perfil_de(user)
        return f"{user.pk}{user.password}{timestamp}{perfil.correo}{perfil.correo_verificado}"


token_verificacion = TokenVerificacion()


def encolar_enlace(usuario: User, verificar: bool = False) -> None:
    generador = token_verificacion if verificar else default_token_generator
    pagina = "verificar-correo" if verificar else "restablecer"
    parametros = urlencode({
        "uid": urlsafe_base64_encode(force_bytes(usuario.pk)),
        "token": generador.make_token(usuario),
    })
    enlace = f"{settings.FRONTEND_URL}/{pagina}#{parametros}"
    CorreoPendiente.objects.create(
        destinatario=perfil_de(usuario).correo,
        asunto="Verifica tu correo" if verificar else "Recupera tu acceso",
        contenido=(f"{enlace}\n\nEste enlace es personal y temporal. "
                   "Si no lo solicitaste, ignora este mensaje."),
    )


def solicitar_recuperacion(correo: str) -> None:
    usuario = usuario_por_correo(correo)
    if usuario and usuario.is_active and usuario.has_usable_password():
        encolar_enlace(usuario)


def usuario_del_token(uid: str, token: str, verificar: bool = False) -> User:
    try:
        identificador = urlsafe_base64_decode(uid).decode()
        usuario = User.objects.get(pk=identificador, is_active=True)
    except (ValueError, TypeError, UnicodeError, OverflowError, User.DoesNotExist, ValidationError):
        raise ErrorEntrada("El enlace no es válido o ya venció.") from None
    generador = token_verificacion if verificar else default_token_generator
    if not generador.check_token(usuario, token):
        raise ErrorEntrada("El enlace no es válido o ya venció.")
    return usuario
