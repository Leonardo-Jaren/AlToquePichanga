import json
from io import StringIO

import pytest
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from rest_framework.test import APIClient

from apps.canchas.models import Cancha
from apps.empresas.models import Empresa, MembresiaEmpresa, RolEmpresa
from apps.horarios.models import (
    ExcepcionHorario,
    HorarioCancha,
    HorarioSede,
    IntervaloHorarioSede,
    TipoExcepcionHorario,
)
from apps.pagos.models import EstadoPagoReserva, MetodoPagoSede, PagoReserva
from apps.reservas.models import EstadoReserva, Reserva
from apps.sedes.models import Sede
from apps.tarifas.models import ReglaTarifa, TipoTarifa
from apps.usuarios.management.commands import generar_datos_demo as comando
from apps.usuarios.services.datos_demo import CORREOS, MARCA

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _activar_debug_para_el_comando(settings):
    """Los tests de comandos locales deben iniciar en el mismo modo permitido."""
    settings.DEBUG = True


def _leer_archivo(ruta) -> dict:
    contenido = ruta.read_text(encoding="utf-8")
    bloque = contenido.split("```json\n", 1)[1].rsplit("\n```", 1)[0]
    return json.loads(bloque)


def _preparar_comando(monkeypatch, tmp_path) -> object:
    monkeypatch.setenv("ALTOQUE_PERMITIR_DATOS_DEMO", "1")
    monkeypatch.setattr(comando, "_ruta_credenciales", lambda: tmp_path / "USUARIOS_PRUEBA_LOCAL.md")
    return tmp_path / "USUARIOS_PRUEBA_LOCAL.md"


def _generar(monkeypatch, tmp_path) -> dict:
    ruta = _preparar_comando(monkeypatch, tmp_path)
    call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())
    return _leer_archivo(ruta)


@pytest.mark.parametrize(
    "debug,opt_in,engine,host",
    [
        (False, "1", "django.db.backends.postgresql", "localhost"),
        (True, None, "django.db.backends.postgresql", "localhost"),
        (True, "1", "django.db.backends.sqlite3", "localhost"),
        (True, "1", "django.db.backends.postgresql", "db.remoto.example"),
    ],
)
def test_guardas_del_comando_fallan_antes_de_escribir(
    monkeypatch, settings, tmp_path, debug, opt_in, engine, host
):
    ruta = _preparar_comando(monkeypatch, tmp_path)
    settings.DEBUG = debug
    base = dict(settings.DATABASES["default"])
    base.update({"ENGINE": engine, "HOST": host})
    settings.DATABASES = {**settings.DATABASES, "default": base}
    if opt_in is None:
        monkeypatch.delenv("ALTOQUE_PERMITIR_DATOS_DEMO", raising=False)
    else:
        monkeypatch.setenv("ALTOQUE_PERMITIR_DATOS_DEMO", opt_in)

    with pytest.raises(CommandError):
        call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())

    assert not ruta.exists()


def test_archivo_local_con_contenido_ajeno_no_se_sobrescribe(monkeypatch, tmp_path):
    ruta = _preparar_comando(monkeypatch, tmp_path)
    ruta.write_text("notas personales\n", encoding="utf-8")

    with pytest.raises(CommandError, match=r"contenido ajeno|no pertenece"):
        call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())

    assert ruta.read_text(encoding="utf-8") == "notas personales\n"
    assert User.objects.count() == 0
    assert Empresa.objects.count() == 0


def test_colision_con_usuario_no_demo_aborta_sin_tocarlo(monkeypatch, tmp_path):
    _preparar_comando(monkeypatch, tmp_path)
    ajeno = User.objects.create_user(
        username="cuenta-ajena", email=CORREOS["superadmin"], password="No cambiar"
    )

    with pytest.raises(CommandError, match="cuenta no demo"):
        call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())

    ajeno.refresh_from_db()
    assert ajeno.username == "cuenta-ajena"
    assert ajeno.check_password("No cambiar")
    assert User.objects.count() == 1
    assert Empresa.objects.count() == 0


def test_creacion_idempotente_y_password_local_estable(monkeypatch, tmp_path):
    ruta = _preparar_comando(monkeypatch, tmp_path)
    call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())
    credenciales_primera = _leer_archivo(ruta)
    hashes_primera = dict(User.objects.values_list("email", "password"))

    call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())
    credenciales_segunda = _leer_archivo(ruta)

    assert credenciales_segunda == credenciales_primera
    assert "Comprobaciones manuales de Fase 4B" in ruta.read_text(encoding="utf-8")
    assert User.objects.count() == 7
    assert Empresa.objects.filter(descripcion__startswith=MARCA).count() == 2
    assert Sede.objects.filter(descripcion__startswith=MARCA).count() == 4
    assert Cancha.objects.filter(descripcion__startswith=MARCA).count() == 6
    assert set(Cancha.objects.filter(publicada=True).values_list("nombre", flat=True)) == {
        f"{MARCA} Cancha A heredada", f"{MARCA} Cancha B Centro 1",
    }
    assert ReglaTarifa.objects.count() == 22
    assert ReglaTarifa.objects.filter(tipo=TipoTarifa.DIURNA).count() == 6
    assert ReglaTarifa.objects.filter(tipo=TipoTarifa.NOCTURNA).count() == 6
    assert ReglaTarifa.objects.filter(tipo=TipoTarifa.FIN_SEMANA).count() == 6
    assert ReglaTarifa.objects.filter(tipo=TipoTarifa.FERIADO).count() == 2
    assert ReglaTarifa.objects.filter(tipo=TipoTarifa.ESPECIAL).count() == 2
    reservas = list(Reserva.objects.select_related("cancha__sede").order_by("cancha__sede__empresa_id", "inicio"))
    assert len(reservas) == 3
    assert {reserva.estado for reserva in reservas} == {
        EstadoReserva.PENDIENTE_VERIFICACION,
        EstadoReserva.PENDIENTE_PAGO,
        EstadoReserva.VENCIDA,
    }
    assert len({reserva.cancha.sede.empresa_id for reserva in reservas}) == 2
    vencida = next(reserva for reserva in reservas if reserva.estado == EstadoReserva.VENCIDA)
    assert vencida.bloques.filter(liberado_en__isnull=True).count() == 0
    assert vencida.historial_estados.count() == 2
    assert MetodoPagoSede.objects.count() == 12
    assert set(PagoReserva.objects.values_list("estado", flat=True)) == {
        EstadoPagoReserva.RECHAZADO,
        EstadoPagoReserva.APROBADO,
        EstadoPagoReserva.PENDIENTE_REVISION,
        EstadoPagoReserva.PENDIENTE_PAGO,
        EstadoPagoReserva.PAGO_TARDIO,
    }
    assert PagoReserva.objects.filter(requiere_conciliacion=True).exists()
    for clave, correo in CORREOS.items():
        usuario = User.objects.get(email=correo)
        assert usuario.is_active
        assert usuario.check_password(credenciales_primera["usuarios"][clave]["contrasena"])
        assert usuario.password == hashes_primera[correo]


def test_actualiza_guia_local_antigua_sin_cambiar_contrasenas(monkeypatch, tmp_path):
    credenciales = _generar(monkeypatch, tmp_path)
    ruta = _preparar_comando(monkeypatch, tmp_path)
    hash_original = dict(User.objects.values_list("email", "password"))
    ruta.write_text(
        comando._renderizar_bloque_credenciales(credenciales)
        + comando._GUIA_LOCAL_ANTERIOR_FASE3D,
        encoding="utf-8",
    )

    call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())

    assert "Comprobaciones manuales de Fase 4B" in ruta.read_text(encoding="utf-8")
    assert _leer_archivo(ruta) == credenciales
    assert dict(User.objects.values_list("email", "password")) == hash_original


def test_migra_guia_de_seis_roles_sin_cambiar_contrasenas_existentes(monkeypatch, tmp_path):
    credenciales = _generar(monkeypatch, tmp_path)
    ruta = _preparar_comando(monkeypatch, tmp_path)
    hash_original = dict(User.objects.values_list("email", "password"))
    version_anterior = {
        **credenciales,
        "usuarios": {
            rol: datos for rol, datos in credenciales["usuarios"].items()
            if rol != "jugador_b"
        },
    }
    ruta.write_text(
        comando._renderizar_bloque_credenciales(version_anterior)
        + comando._GUIA_LOCAL_ANTERIOR_FASE4A,
        encoding="utf-8",
    )

    call_command("generar_datos_demo", stdout=StringIO(), stderr=StringIO())

    actualizado = _leer_archivo(ruta)
    assert set(actualizado["usuarios"]) == set(CORREOS)
    for rol in set(CORREOS) - {"jugador_b"}:
        assert actualizado["usuarios"][rol] == credenciales["usuarios"][rol]
    assert actualizado["usuarios"]["jugador_b"]["correo"] == CORREOS["jugador_b"]
    assert User.objects.get(email=CORREOS["jugador_b"]).check_password(
        actualizado["usuarios"]["jugador_b"]["contrasena"]
    )
    for correo, hash_guardado in hash_original.items():
        if correo != CORREOS["jugador_b"]:
            assert User.objects.get(email=correo).password == hash_guardado


def test_fixture_de_horarios_incluye_herencia_horario_propio_y_excepciones(
    monkeypatch, tmp_path
):
    _generar(monkeypatch, tmp_path)
    cancha_heredada = Cancha.objects.get(nombre=f"{MARCA} Cancha A heredada")
    cancha_propia = Cancha.objects.get(nombre=f"{MARCA} Cancha A con horario propio")
    horario_heredado = HorarioCancha.objects.get(cancha=cancha_heredada)
    horario_propio = HorarioCancha.objects.get(cancha=cancha_propia)

    assert horario_heredado.hereda_horario_sede
    assert horario_heredado.dias_heredados == []
    assert not horario_propio.hereda_horario_sede
    assert horario_propio.dias_heredados == [5, 6]
    assert set(horario_propio.intervalos.values_list("dia_semana", flat=True)) == {0, 1, 2, 3, 4}
    assert HorarioSede.objects.filter(configurado=True).count() == 4
    assert IntervaloHorarioSede.objects.count() == 28
    assert ExcepcionHorario.objects.filter(
        tipo=TipoExcepcionHorario.AMPLIACION,
        sede__empresa__nombre__contains=f"{MARCA} Complejos Pichanga A",
        motivo__contains="Ampliación especial",
    ).exists()
    assert ExcepcionHorario.objects.filter(
        tipo=TipoExcepcionHorario.CIERRE,
        cancha=cancha_propia,
        motivo__contains="mantenimiento",
    ).exists()


def test_fixture_de_tarifas_cubre_dos_empresas_y_bloques_operativos(monkeypatch, tmp_path):
    credenciales = _generar(monkeypatch, tmp_path)
    empresas = set(ReglaTarifa.objects.values_list("cancha__sede__empresa_id", flat=True))
    assert len(empresas) == 2
    cancha_a = Cancha.objects.get(nombre=f"{MARCA} Cancha A heredada")
    cancha_b = Cancha.objects.get(nombre=f"{MARCA} Cancha B Centro 1")
    assert ReglaTarifa.objects.filter(cancha=cancha_a, tipo=TipoTarifa.DIURNA).exists()
    assert ReglaTarifa.objects.filter(cancha=cancha_a, tipo=TipoTarifa.NOCTURNA).exists()
    assert ReglaTarifa.objects.filter(cancha=cancha_a, tipo=TipoTarifa.FIN_SEMANA).exists()
    assert ReglaTarifa.objects.filter(cancha=cancha_a, tipo=TipoTarifa.FERIADO).exists()
    assert ReglaTarifa.objects.filter(cancha=cancha_a, tipo=TipoTarifa.ESPECIAL).exists()

    dueno_a, _, _ = _iniciar_sesion("dueno_a", credenciales)
    cajero_a, _, _ = _iniciar_sesion("cajero_a", credenciales)
    assert dueno_a.get(f"/api/canchas/{cancha_a.pk}/tarifas/").status_code == 200
    assert cajero_a.get(f"/api/canchas/{cancha_a.pk}/tarifas/").status_code == 200
    assert dueno_a.get(f"/api/canchas/{cancha_b.pk}/tarifas/").status_code == 404


def _iniciar_sesion(clave: str, credenciales: dict) -> tuple[APIClient, dict, str]:
    correo = CORREOS[clave]
    cliente = APIClient(enforce_csrf_checks=True)
    token = cliente.get("/api/auth/csrf/").data["csrfToken"]
    respuesta = cliente.post(
        "/api/auth/login/",
        {"correo": correo, "contrasena": credenciales["usuarios"][clave]["contrasena"]},
        format="json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert respuesta.status_code == 200, respuesta.data
    # El login rota el token CSRF; las mutaciones deben usar el posterior al login.
    token = cliente.get("/api/auth/csrf/").data["csrfToken"]
    return cliente, respuesta.data, token


def test_todas_las_cuentas_activas_entran_por_login_normal(monkeypatch, tmp_path):
    credenciales = _generar(monkeypatch, tmp_path)
    roles = {
        "superadmin": (True, [], "plataforma"),
        "dueno_a": (False, [RolEmpresa.DUENO], "dueno"),
        "dueno_b": (False, [RolEmpresa.DUENO], "dueno"),
        "admin_a": (False, [RolEmpresa.ADMINISTRADOR_SEDE], "administrador_sede"),
        "cajero_a": (False, [RolEmpresa.CAJERO], "cajero"),
        "jugador": (False, [], "jugador"),
    }

    for clave, (global_admin, membresias_esperadas, ruta_panel) in roles.items():
        cliente, perfil, _ = _iniciar_sesion(clave, credenciales)
        assert User.objects.get(email=CORREOS[clave]).is_active
        assert perfil["es_superadministrador"] is global_admin
        assert [item["rol"] for item in perfil["membresias"]] == membresias_esperadas
        assert cliente.get("/api/auth/perfil/").status_code == 200
        assert cliente.get(f"/api/panel/{ruta_panel}/").status_code == 200


def test_login_resuelve_aislamiento_de_empresa_sede_y_cajero(monkeypatch, tmp_path):
    credenciales = _generar(monkeypatch, tmp_path)
    sede_a = Sede.objects.get(nombre=f"{MARCA} Sede A Centro")
    sede_a_norte = Sede.objects.get(nombre=f"{MARCA} Sede A Norte")
    sedes_b = list(Sede.objects.filter(nombre__contains=f"{MARCA} Sede B"))
    cancha_b = Cancha.objects.filter(sede__in=sedes_b).first()

    dueno_a, _, _ = _iniciar_sesion("dueno_a", credenciales)
    dueno_b, _, _ = _iniciar_sesion("dueno_b", credenciales)
    admin_a, _, token_admin = _iniciar_sesion("admin_a", credenciales)
    cajero_a, _, token_cajero = _iniciar_sesion("cajero_a", credenciales)
    jugador, perfil_jugador, _ = _iniciar_sesion("jugador", credenciales)
    plataforma, _, _ = _iniciar_sesion("superadmin", credenciales)

    assert dueno_a.get(f"/api/canchas/{cancha_b.pk}/").status_code == 404
    assert dueno_b.get(f"/api/canchas/{cancha_b.pk}/").status_code == 200
    assert dueno_a.get(f"/api/sedes/?empresa={cancha_b.sede.empresa_id}").data == []
    assert len(dueno_b.get(f"/api/sedes/?empresa={cancha_b.sede.empresa_id}").data) == 2
    sedes_admin = admin_a.get("/api/sedes/").data
    assert [item["id"] for item in sedes_admin] == [sede_a.pk]
    assert admin_a.get(f"/api/sedes/{sede_a_norte.pk}/horario-semanal/").status_code == 404
    assert perfil_jugador["membresias"] == []
    assert jugador.get("/api/sedes/").data == []

    cambio = cajero_a.put(
        f"/api/sedes/{sede_a.pk}/horario-semanal/",
        {"intervalos": [{"dia_semana": 0, "hora_apertura": "09:00", "hora_cierre": "17:00"}]},
        format="json",
        HTTP_X_CSRFTOKEN=token_cajero,
    )
    assert cambio.status_code == 403
    assert IntervaloHorarioSede.objects.filter(horario__sede=sede_a, dia_semana=0).first().hora_apertura.strftime("%H:%M") == "15:00"

    plataforma_sedes = plataforma.get("/api/sedes/")
    assert plataforma_sedes.status_code == 200
    assert len(plataforma_sedes.data) == 4
    assert plataforma.get("/api/canchas/").data["count"] == 6

    cambio_admin_no_asignado = admin_a.put(
        f"/api/sedes/{sede_a_norte.pk}/horario-semanal/",
        {"intervalos": []},
        format="json",
        HTTP_X_CSRFTOKEN=token_admin,
    )
    assert cambio_admin_no_asignado.status_code == 404


def test_membresias_y_asignaciones_demo_son_activas(monkeypatch, tmp_path):
    _generar(monkeypatch, tmp_path)
    assert MembresiaEmpresa.objects.filter(
        usuario__email=CORREOS["dueno_a"], empresa__nombre__contains="Pichanga A",
        rol=RolEmpresa.DUENO, activa=True,
    ).exists()
    for clave, rol in (("admin_a", RolEmpresa.ADMINISTRADOR_SEDE), ("cajero_a", RolEmpresa.CAJERO)):
        assert MembresiaEmpresa.objects.filter(
            usuario__email=CORREOS[clave], rol=rol, activa=True,
            sedes_asignadas__sede__nombre=f"{MARCA} Sede A Centro",
            sedes_asignadas__activa=True,
        ).exists()
    assert not MembresiaEmpresa.objects.filter(usuario__email=CORREOS["jugador"]).exists()
