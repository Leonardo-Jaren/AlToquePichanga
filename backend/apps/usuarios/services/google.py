import base64
import hashlib
import secrets
import time
from urllib.parse import urlencode
from uuid import uuid4

import requests
from django.conf import settings
from django.contrib.auth import login
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2 import id_token
from rest_framework.exceptions import APIException, ValidationError

from apps.usuarios.models import IdentidadGoogle, PerfilUsuario
from apps.usuarios.repositories.usuarios import perfil_de, usuario_por_correo


class GoogleNoDisponible(APIException):
    status_code = 503
    default_detail = "Google pendiente de configuración. Ingresa con tu correo."


class TransporteGoogle(Request):
    def __call__(self, *args, **kwargs):
        kwargs["timeout"] = 10
        return super().__call__(*args, **kwargs)


def iniciar_google(request, vincular: bool) -> str:
    if not all([settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET, settings.GOOGLE_REDIRECT_URI]):
        raise GoogleNoDisponible()
    if vincular and not request.user.is_authenticated:
        raise ValidationError("Inicia sesión antes de vincular Google.")
    if request.user.is_authenticated and not vincular:
        raise ValidationError("Cierra tu sesión o vincula Google desde tu perfil.")
    estado, nonce, verificador = (secrets.token_urlsafe(32) for _ in range(3))
    request.session["google_pendiente"] = {
        "estado": estado, "nonce": nonce, "verificador": verificador,
        "emitido": time.time(), "usuario_id": request.user.pk if vincular else None,
    }
    reto = base64.urlsafe_b64encode(hashlib.sha256(verificador.encode()).digest()).rstrip(b"=").decode()
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": settings.GOOGLE_CLIENT_ID, "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code", "scope": "openid email profile", "state": estado,
        "nonce": nonce, "code_challenge": reto, "code_challenge_method": "S256",
        "prompt": "select_account",
    })


def intercambiar_codigo(codigo: str, verificador: str) -> dict:
    try:
        respuesta = requests.post("https://oauth2.googleapis.com/token", data={
            "code": codigo, "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code", "code_verifier": verificador,
        }, timeout=10)
        respuesta.raise_for_status()
        token = respuesta.json()["id_token"]
        # Biblioteca oficial: firma, audiencia, emisor y expiración; nonce se valida abajo.
        return id_token.verify_oauth2_token(token, TransporteGoogle(), settings.GOOGLE_CLIENT_ID)
    except (requests.RequestException, GoogleAuthError, ValueError, KeyError, TypeError):
        raise ValidationError("No fue posible verificar la identidad de Google.") from None


def resolver_identidad(datos: dict, usuario_vinculado: User | None) -> User:
    correo = datos["email"].strip().lower()
    with transaction.atomic():
        identidad = IdentidadGoogle.objects.select_related("usuario").filter(
            identificador=datos["sub"]
        ).first()
        if identidad:
            if usuario_vinculado and identidad.usuario_id != usuario_vinculado.pk:
                raise ValidationError("Esta identidad ya está vinculada a otra cuenta.")
            usuario = identidad.usuario
        elif usuario_vinculado:
            if (perfil_de(usuario_vinculado).correo != correo
                    or IdentidadGoogle.objects.filter(usuario=usuario_vinculado).exists()):
                raise ValidationError("Utiliza la cuenta de Google con el correo de tu perfil.")
            usuario = usuario_vinculado
            IdentidadGoogle.objects.create(usuario=usuario, identificador=datos["sub"])
            perfil = perfil_de(usuario)
            perfil.correo_verificado = True
            perfil.save(update_fields=["correo_verificado"])
        else:
            if usuario_por_correo(correo):
                raise ValidationError("Inicia sesión con tu contraseña y vincula Google desde tu perfil.")
            usuario = User(username=uuid4().hex, email=correo,
                           first_name=str(datos.get("given_name", "Jugador"))[:150],
                           last_name=str(datos.get("family_name", ""))[:150])
            usuario.set_unusable_password()
            usuario.save()
            PerfilUsuario.objects.create(usuario=usuario, correo=correo, correo_verificado=True)
            IdentidadGoogle.objects.create(usuario=usuario, identificador=datos["sub"])
        if not usuario.is_active:
            raise ValidationError("Esta cuenta no está disponible.")
        return usuario


def completar_google(request) -> None:
    pendiente = request.session.pop("google_pendiente", None)
    estado = request.query_params.get("state", "")
    if (not pendiente or not secrets.compare_digest(estado, pendiente["estado"])
            or time.time() - pendiente["emitido"] > 600
            or request.query_params.get("error") or not request.query_params.get("code")):
        raise ValidationError("La autorización no es válida o venció. Intenta nuevamente.")
    vinculado = pendiente["usuario_id"]
    if vinculado and (not request.user.is_authenticated or request.user.pk != vinculado):
        raise ValidationError("La sesión de vinculación cambió. Intenta nuevamente.")
    datos = intercambiar_codigo(request.query_params["code"], pendiente["verificador"])
    if (datos.get("nonce") != pendiente["nonce"] or datos.get("email_verified") is not True
            or not isinstance(datos.get("sub"), str) or not datos["sub"]
            or len(datos["sub"]) > 255 or not isinstance(datos.get("email"), str)
            or len(datos["email"]) > 254 or "@" not in datos["email"]):
        raise ValidationError("La identidad de Google no tiene un correo verificado válido.")
    try:
        usuario = resolver_identidad(datos, request.user if vinculado else None)
    except IntegrityError:
        raise ValidationError("No se pudo vincular esta cuenta. Intenta nuevamente desde tu perfil.") from None
    login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
