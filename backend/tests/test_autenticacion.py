from io import StringIO
from urllib.parse import parse_qs, urlsplit

import pytest
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from apps.empresas.models import Empresa, MembresiaEmpresa, RolEmpresa
from apps.usuarios.models import CorreoPendiente

pytestmark = pytest.mark.django_db
REGISTRO = {"correo": "jugador@example.com", "nombre": "Jugador",
            "apellidos": "Prueba", "contrasena": "Pichanga-fuerte-927!"}


@pytest.fixture
def cliente():
    return APIClient(enforce_csrf_checks=True)


def enviar(cliente, ruta, datos=None, metodo="post"):
    token = cliente.get("/api/auth/csrf/").data["csrfToken"]
    return getattr(cliente, metodo)(ruta, datos or {}, format="json", HTTP_X_CSRFTOKEN=token)


@pytest.fixture
def jugador(cliente):
    assert enviar(cliente, "/api/auth/registro/", REGISTRO).status_code == 201
    return User.objects.get(email=REGISTRO["correo"])


def test_registro_sesion_perfil_y_logout(cliente, jugador):
    assert jugador.check_password(REGISTRO["contrasena"])
    assert not jugador.is_staff and not jugador.is_superuser
    assert cliente.cookies["sessionid"]["httponly"]
    assert cliente.get("/api/auth/perfil/").data["es_jugador"]
    respuesta = enviar(cliente, "/api/auth/perfil/", {"nombre": "Nuevo"}, "patch")
    assert respuesta.data["nombre"] == "Nuevo"
    assert respuesta.data["membresias"] == []
    assert enviar(cliente, "/api/auth/logout/").status_code == 204
    assert cliente.get("/api/auth/perfil/").status_code == 401


@pytest.mark.parametrize("extra", [{"rol": "dueno"}, {"is_superuser": True},
                                  {"empresa_id": 1}, {"is_staff": True}])
def test_registro_no_acepta_elevacion(cliente, extra):
    assert enviar(cliente, "/api/auth/registro/", {**REGISTRO, **extra}).status_code == 400
    assert User.objects.count() == 0


@pytest.mark.parametrize("campo,valor", [("correo", "invalido"), ("contrasena", "123"),
                                        ("nombre", "")])
def test_registro_invalido(cliente, campo, valor):
    assert enviar(cliente, "/api/auth/registro/", {**REGISTRO, campo: valor}).status_code == 400


def test_correo_duplicado_normalizado(cliente, jugador):
    assert enviar(cliente, "/api/auth/registro/", {
        **REGISTRO, "correo": REGISTRO["correo"].upper()
    }).status_code == 400
    assert User.objects.count() == 1


def test_login_correcto_incorrecto_e_inactivo(cliente, jugador):
    enviar(cliente, "/api/auth/logout/")
    datos = {"correo": REGISTRO["correo"], "contrasena": "incorrecta"}
    assert enviar(cliente, "/api/auth/login/", datos).status_code == 401
    datos["contrasena"] = REGISTRO["contrasena"]
    assert enviar(cliente, "/api/auth/login/", datos).status_code == 200
    enviar(cliente, "/api/auth/logout/")
    jugador.is_active = False
    jugador.save()
    assert enviar(cliente, "/api/auth/login/", datos).status_code == 401


def test_csrf_requerido_incluso_anonimos(cliente):
    assert cliente.post("/api/auth/login/", REGISTRO, format="json").status_code == 403
    assert cliente.post("/api/auth/registro/", REGISTRO, format="json").status_code == 403


def test_limite_intentos_compartido_entre_sesiones(cliente, settings):
    settings.AUTH_LOGIN_LIMIT = 2
    datos = {"correo": "nadie@example.com", "contrasena": "incorrecta"}
    assert enviar(cliente, "/api/auth/login/", datos).status_code == 401
    assert enviar(APIClient(enforce_csrf_checks=True), "/api/auth/login/", datos).status_code == 401
    assert enviar(cliente, "/api/auth/login/", datos).status_code == 429


def parametros_correo():
    contenido = CorreoPendiente.objects.latest("id").contenido
    return {k: v[0] for k, v in parse_qs(urlsplit(contenido.splitlines()[0]).fragment).items()}


def test_recuperacion_no_enumera_y_token_un_solo_uso(cliente, jugador):
    existe = enviar(cliente, "/api/auth/recuperar/", {"correo": REGISTRO["correo"]})
    token = parametros_correo()
    no_existe = enviar(cliente, "/api/auth/recuperar/", {"correo": "nadie@example.com"})
    assert existe.status_code == no_existe.status_code == 200
    assert existe.data == no_existe.data
    datos = {**token, "contrasena": "Otra-clave-segura-492!"}
    assert enviar(cliente, "/api/auth/restablecer/", datos).status_code == 200
    assert enviar(cliente, "/api/auth/restablecer/", datos).status_code == 400
    assert cliente.get("/api/auth/perfil/").status_code == 401


def test_token_invalido_y_contrasena_debil(cliente, jugador):
    enviar(cliente, "/api/auth/recuperar/", {"correo": REGISTRO["correo"]})
    token = parametros_correo()
    assert enviar(cliente, "/api/auth/restablecer/", {
        **token, "contrasena": "123"
    }).status_code == 400
    assert enviar(cliente, "/api/auth/restablecer/", {
        **token, "token": "falso", "contrasena": REGISTRO["contrasena"]
    }).status_code == 400


def test_verificacion_y_cola_correo_con_reintento(cliente, jugador, settings, monkeypatch):
    token = parametros_correo()
    assert enviar(cliente, "/api/auth/verificar-correo/", token).status_code == 200
    jugador.perfil.refresh_from_db()
    assert jugador.perfil.correo_verificado
    assert enviar(cliente, "/api/auth/verificar-correo/", token).status_code == 400
    settings.MAILERS = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
    call_command("enviar_correos", stdout=StringIO())
    assert len(mail.outbox) == 1
    correo = CorreoPendiente.objects.get()
    assert correo.enviado_en and correo.contenido == ""
    correo.pk = None
    correo.enviado_en = None
    correo.proximo_intento = timezone.now()
    correo.save()
    def fallo(*args, **kwargs):
        raise OSError("SMTP no disponible")
    monkeypatch.setattr("apps.usuarios.management.commands.enviar_correos.send_mail", fallo)
    call_command("enviar_correos", stdout=StringIO(), stderr=StringIO())
    correo.refresh_from_db()
    assert correo.enviado_en is None and correo.intentos == 2


def test_api_aislamiento_y_paneles(cliente, jugador):
    propia = Empresa.objects.create(nombre="Propia")
    ajena = Empresa.objects.create(nombre="Ajena")
    assert cliente.get("/api/panel/dueno/").status_code == 403
    assert cliente.get("/api/panel/plataforma/").status_code == 403
    MembresiaEmpresa.objects.create(usuario=jugador, empresa=propia, rol=RolEmpresa.DUENO)
    assert cliente.get("/api/panel/dueno/").status_code == 200
    assert cliente.get(f"/api/empresas/{propia.id}/").status_code == 200
    assert cliente.get(f"/api/empresas/{ajena.id}/").status_code == 404
    assert enviar(cliente, "/api/auth/perfil/", {"nombre": "X", "is_superuser": True},
                  "patch").status_code == 400
    jugador.is_superuser = True
    jugador.save()
    assert cliente.get(f"/api/empresas/{ajena.id}/").status_code == 200
