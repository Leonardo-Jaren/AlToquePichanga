from concurrent.futures import ThreadPoolExecutor
from io import StringIO
from threading import Barrier
from unittest.mock import Mock

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import close_old_connections
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.usuarios.models import PerfilUsuario
from apps.usuarios.services.correos import usuario_del_token
from tests.test_autenticacion import REGISTRO, enviar, parametros_correo


@pytest.mark.django_db(transaction=True)
def test_dos_registros_simultaneos_no_duplican_correo():
    barrera = Barrier(2)

    def registrar(_):
        close_old_connections()
        try:
            cliente = APIClient(enforce_csrf_checks=True)
            barrera.wait(timeout=10)
            return enviar(cliente, "/api/auth/registro/", REGISTRO).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as ejecutor:
        resultados = list(ejecutor.map(registrar, range(2)))
    assert sorted(resultados) == [201, 400]
    assert User.objects.count() == PerfilUsuario.objects.count() == 1


@pytest.mark.django_db
def test_cookie_rotada_y_cierre_invalida_la_sesion():
    cliente = APIClient(enforce_csrf_checks=True)
    enviar(cliente, "/api/auth/registro/", REGISTRO)
    sesion_original = cliente.cookies["sessionid"].value
    enviar(cliente, "/api/auth/login/", {
        "correo": REGISTRO["correo"], "contrasena": REGISTRO["contrasena"],
    })
    sesion_activa = cliente.cookies["sessionid"].value
    assert sesion_activa != sesion_original
    enviar(cliente, "/api/auth/logout/")
    cliente.cookies["sessionid"] = sesion_activa
    assert cliente.get("/api/auth/perfil/").status_code == 401


@pytest.mark.django_db
def test_token_vencido_y_cache_privada(monkeypatch):
    cliente = APIClient(enforce_csrf_checks=True)
    enviar(cliente, "/api/auth/registro/", REGISTRO)
    enviar(cliente, "/api/auth/recuperar/", {"correo": REGISTRO["correo"]})
    parametros = parametros_correo()
    from django.contrib.auth.tokens import default_token_generator
    ahora = default_token_generator._now()
    from datetime import timedelta
    monkeypatch.setattr(default_token_generator, "_now", lambda: ahora + timedelta(hours=2))
    with pytest.raises(ValidationError):
        usuario_del_token(**parametros)
    assert cliente.get("/api/auth/perfil/")["Cache-Control"] == "no-store"


@pytest.mark.django_db
def test_origen_no_autorizado_y_formato_invalido():
    cliente = APIClient(enforce_csrf_checks=True)
    csrf = cliente.get("/api/auth/csrf/").data["csrfToken"]
    respuesta = cliente.post("/api/auth/registro/", REGISTRO, format="json",
                             HTTP_X_CSRFTOKEN=csrf, HTTP_ORIGIN="https://ajeno.example")
    assert respuesta.status_code == 403
    assert enviar(cliente, "/api/auth/registro/", ["no-es-un-objeto"]).status_code == 400


@pytest.mark.django_db
def test_superusuario_provisionado_con_perfil_puede_ingresar():
    usuario = User.objects.create_superuser(username="plataforma", email="admin@example.com",
                                           password=REGISTRO["contrasena"])
    call_command("sincronizar_perfiles", stdout=StringIO())
    cliente = APIClient(enforce_csrf_checks=True)
    respuesta = enviar(cliente, "/api/auth/login/", {
        "correo": usuario.email, "contrasena": REGISTRO["contrasena"],
    })
    assert respuesta.status_code == 200 and respuesta.data["es_superadministrador"]


@pytest.mark.django_db
def test_salud_no_expone_excepcion_de_base_de_datos(monkeypatch):
    from django.db import OperationalError
    monkeypatch.setattr("shared.views.connection.cursor", Mock(side_effect=OperationalError("dato-privado")))
    respuesta = APIClient().get("/api/health/")
    assert respuesta.status_code == 503
    assert "dato-privado" not in str(respuesta.data)
