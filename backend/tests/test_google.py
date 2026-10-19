import json
import time
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import parse_qs, urlsplit

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.contrib.auth.models import User
from google.auth import crypt, jwt
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.usuarios.models import IdentidadGoogle, PerfilUsuario
from apps.usuarios.services.google import intercambiar_codigo

pytestmark = pytest.mark.django_db


@pytest.fixture
def google(settings):
    settings.GOOGLE_CLIENT_ID = "cliente-prueba"
    settings.GOOGLE_CLIENT_SECRET = "secreto-simulado"
    settings.GOOGLE_REDIRECT_URI = "http://localhost:8000/api/auth/google/retorno/"
    return APIClient(enforce_csrf_checks=True)


def iniciar(cliente, vincular=False):
    csrf = cliente.get("/api/auth/csrf/").data["csrfToken"]
    return cliente.post("/api/auth/google/iniciar/", {"vincular": vincular}, format="json",
                        HTTP_X_CSRFTOKEN=csrf)


def simular(google, monkeypatch, cambios=None):
    pendiente = google.session["google_pendiente"]
    claims = {"sub": "google-id-1", "email": "jugador@example.com", "email_verified": True,
              "given_name": "Jugador", "nonce": pendiente["nonce"], **(cambios or {})}
    proveedor = Mock(return_value=claims)
    monkeypatch.setattr("apps.usuarios.services.google.intercambiar_codigo", proveedor)
    return pendiente, proveedor


def retorno(cliente, pendiente, **extra):
    return cliente.get("/api/auth/google/retorno/", {
        "state": pendiente["estado"], "code": "codigo-simulado", **extra,
    })


def test_google_nueva_cuenta_y_login_por_identidad(google, monkeypatch):
    respuesta = iniciar(google)
    parametros = parse_qs(urlsplit(respuesta.data["url"]).query)
    assert parametros["code_challenge_method"] == ["S256"]
    assert parametros["scope"] == ["openid email profile"]
    pendiente, proveedor = simular(google, monkeypatch)
    assert "error" not in retorno(google, pendiente).url
    usuario = User.objects.get()
    assert not usuario.has_usable_password()
    assert usuario.perfil.correo_verificado
    assert not usuario.is_superuser
    assert google.get("/api/auth/perfil/").status_code == 200
    proveedor.assert_called_once_with("codigo-simulado", pendiente["verificador"])
    google.logout()
    iniciar(google)
    pendiente, _ = simular(google, monkeypatch, {"email": "otro@example.com"})
    assert "error" not in retorno(google, pendiente).url
    assert User.objects.count() == 1


@pytest.mark.parametrize("cambios", [{"nonce": "otro"}, {"email_verified": False},
                                    {"email_verified": "true"}, {"sub": ""}, {"email": ""}])
def test_identidad_no_verificada_o_nonce_incorrecto(google, monkeypatch, cambios):
    iniciar(google)
    pendiente, _ = simular(google, monkeypatch, cambios)
    assert "error=autorizacion" in retorno(google, pendiente).url
    assert User.objects.count() == 0


def test_state_expiracion_y_reutilizacion(google, monkeypatch):
    iniciar(google)
    pendiente, proveedor = simular(google, monkeypatch)
    assert "error" in retorno(google, pendiente, state="otro").url
    proveedor.assert_not_called()
    assert "error" in retorno(google, pendiente).url
    iniciar(google)
    sesion = google.session
    sesion["google_pendiente"] = {**sesion["google_pendiente"], "emitido": time.time() - 601}
    sesion.save()
    assert "error" in retorno(google, sesion["google_pendiente"]).url
    proveedor.assert_not_called()


def test_correo_local_no_se_vincula_automaticamente(google, monkeypatch):
    usuario = User.objects.create_user(username="local", email="jugador@example.com")
    PerfilUsuario.objects.create(usuario=usuario, correo=usuario.email)
    iniciar(google)
    pendiente, _ = simular(google, monkeypatch)
    assert "error" in retorno(google, pendiente).url
    assert not IdentidadGoogle.objects.exists()
    assert google.get("/api/auth/perfil/").status_code == 401


def test_vinculacion_exige_sesion_y_mismo_correo(google, monkeypatch):
    assert iniciar(google, vincular=True).status_code == 400
    usuario = User.objects.create_user(username="local", email="jugador@example.com")
    PerfilUsuario.objects.create(usuario=usuario, correo=usuario.email)
    google.force_login(usuario)
    assert iniciar(google).status_code == 400
    assert iniciar(google, vincular=True).status_code == 200
    pendiente, _ = simular(google, monkeypatch, {"email": "ajeno@example.com"})
    assert "error" in retorno(google, pendiente).url
    assert not IdentidadGoogle.objects.exists()
    iniciar(google, vincular=True)
    pendiente, _ = simular(google, monkeypatch)
    assert "error" not in retorno(google, pendiente).url
    assert IdentidadGoogle.objects.get().usuario_id == usuario.pk


def test_cuenta_inactiva_no_ingresa(google, monkeypatch):
    usuario = User.objects.create_user(username="inactivo", is_active=False)
    IdentidadGoogle.objects.create(usuario=usuario, identificador="google-id-1")
    iniciar(google)
    pendiente, _ = simular(google, monkeypatch)
    assert "error" in retorno(google, pendiente).url
    assert google.get("/api/auth/perfil/").status_code == 401


def test_sin_credenciales_o_callback_cancelado(google, settings, monkeypatch):
    iniciar(google)
    pendiente, proveedor = simular(google, monkeypatch)
    assert "error" in retorno(google, pendiente, error="access_denied").url
    proveedor.assert_not_called()
    settings.GOOGLE_CLIENT_ID = ""
    assert iniciar(google).status_code == 503


@pytest.mark.parametrize("alteracion", ["ninguna", "audiencia", "emisor", "vencido", "firma"])
def test_validador_real_firma_audiencia_emisor_expiracion(google, monkeypatch, alteracion):
    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    privado = clave.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                 serialization.NoEncryption())
    publico = clave.public_key().public_bytes(serialization.Encoding.PEM,
                                             serialization.PublicFormat.SubjectPublicKeyInfo)
    claims = {"iss": "https://accounts.google.com", "aud": "cliente-prueba",
              "iat": int(time.time()) - 10, "exp": int(time.time()) + 600, "sub": "id-1"}
    if alteracion == "audiencia":
        claims["aud"] = "otro-cliente"
    if alteracion == "emisor":
        claims["iss"] = "https://atacante.example"
    if alteracion == "vencido":
        claims["exp"] = int(time.time()) - 1
    token = jwt.encode(crypt.RSASigner.from_string(privado, key_id="prueba"), claims).decode()
    if alteracion == "firma":
        token = token[:-8] + "abcdefgh"
    respuesta = Mock()
    respuesta.json.return_value = {"id_token": token}
    monkeypatch.setattr("apps.usuarios.services.google.requests.post", Mock(return_value=respuesta))
    monkeypatch.setattr("apps.usuarios.services.google.TransporteGoogle.__call__",
                        lambda *args, **kwargs: SimpleNamespace(
                            status=200, data=json.dumps({"prueba": publico.decode()}).encode()))
    if alteracion == "ninguna":
        assert intercambiar_codigo("codigo", "verificador")["sub"] == "id-1"
    else:
        with pytest.raises(ValidationError):
            intercambiar_codigo("codigo", "verificador")
