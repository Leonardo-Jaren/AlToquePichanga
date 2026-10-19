from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from django.conf import settings as django_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.canchas.models import Cancha, EstadoCancha, ImagenCancha
from apps.empresas.models import (
    AccesoPlataforma,
    Empresa,
    EstadoEmpresa,
    MembresiaEmpresa,
    RegistroAuditoria,
    RolEmpresa,
)
from apps.sedes.models import AsignacionSede, Sede
from apps.suscripciones.models import (
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    PlanSuscripcion,
    SuscripcionEmpresa,
)
from apps.usuarios.models import PerfilUsuario

pytestmark = pytest.mark.django_db

PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"


@pytest.fixture
def media_root(settings):
    with TemporaryDirectory(prefix=".pytest-media-canchas-", dir=django_settings.BASE_DIR) as path:
        settings.MEDIA_ROOT = Path(path)
        yield Path(path)


def usuario(correo: str, *, superusuario: bool = False) -> User:
    user = User.objects.create_user(
        username=correo, email=correo, password="AlToque-test-493!",
        is_superuser=superusuario, is_staff=superusuario,
    )
    PerfilUsuario.objects.create(usuario=user, correo=correo)
    return user


def cliente(user: User) -> APIClient:
    api = APIClient()
    api.force_authenticate(user)
    return api


def empresa_con_suscripcion(owner: User, nombre: str, limite: int | None = None):
    empresa = Empresa.objects.create(
        nombre=nombre, estado=EstadoEmpresa.ACTIVA, activa=True
    )
    MembresiaEmpresa.objects.create(
        usuario=owner, empresa=empresa, rol=RolEmpresa.DUENO
    )
    plan = PlanSuscripcion.objects.create(
        nombre=f"Plan {nombre}", precio=Decimal("20.00"), moneda="PEN",
        frecuencia=FrecuenciaSuscripcion.MENSUAL, maximo_canchas=limite,
    )
    hoy = timezone.localdate()
    SuscripcionEmpresa.objects.create(
        empresa=empresa, plan=plan, estado=EstadoSuscripcion.ACTIVA,
        fecha_inicio=hoy, fecha_vencimiento=hoy + timedelta(days=30),
        importe_acordado=plan.precio, moneda_acordada=plan.moneda,
        frecuencia_acordada=plan.frecuencia,
    )
    return empresa


def sede(empresa: Empresa, nombre: str = "Complejo Centro") -> Sede:
    return Sede.objects.create(empresa=empresa, nombre=nombre, direccion="Av. Lima 100")


def datos_cancha(sede_id: int, **cambios) -> dict:
    datos = {
        "sede_id": sede_id,
        "nombre": "Cancha Norte",
        "descripcion": "Fútbol rápido",
        "modalidad": 7,
        "tipo_superficie": "Sintético",
        "capacidad_jugadores": 14,
        "techada": True,
        "iluminacion": True,
        "caracteristicas": ["Duchas", "Estacionamiento"],
    }
    datos.update(cambios)
    return datos


def crear_por_api(api: APIClient, sede_id: int, **cambios) -> dict:
    respuesta = api.post("/api/canchas/", datos_cancha(sede_id, **cambios), format="json")
    assert respuesta.status_code == 201, respuesta.data
    return respuesta.data


def test_crud_filtros_paginacion_y_auditoria():
    propietario = usuario("dueno-canchas@example.com")
    empresa = empresa_con_suscripcion(propietario, "Huánuco Fútbol")
    centro = sede(empresa, "Complejo Centro")
    norte = sede(empresa, "Complejo Norte")
    api = cliente(propietario)
    primera = crear_por_api(api, centro.pk)
    crear_por_api(api, norte.pk, nombre="Cancha 11", modalidad=11)

    listado = api.get(
        f"/api/canchas/?sede={centro.pk}&modalidad=7&buscar=Norte&page_size=1"
    )
    assert listado.status_code == 200
    assert listado.data == {
        "count": 1, "next": None, "previous": None,
        "results": [primera],
    }
    detalle = api.get(f"/api/canchas/{primera['id']}/")
    assert detalle.data["empresa_id"] == empresa.pk
    assert detalle.data["sede"] == centro.nombre

    editado = api.patch(
        f"/api/canchas/{primera['id']}/",
        {"nombre": "Cancha Techada", "modalidad": 8}, format="json",
    )
    assert editado.status_code == 200
    assert editado.data["nombre"] == "Cancha Techada"
    assert editado.data["modalidad"] == 8
    transferencia = api.patch(
        f"/api/canchas/{primera['id']}/", {"sede_id": norte.pk}, format="json"
    )
    assert transferencia.status_code == 400
    assert RegistroAuditoria.objects.filter(recurso="cancha", empresa=empresa).count() == 3


def test_validacion_de_modalidad_capacidad_y_campos_estrictos():
    propietario = usuario("validacion-canchas@example.com")
    empresa = empresa_con_suscripcion(propietario, "Empresa Validación")
    ubicacion = sede(empresa)
    api = cliente(propietario)

    for extras in (
        {"modalidad": 0},
        {"modalidad": 32768},
        {"capacidad_jugadores": 0},
        {"nombre": "   "},
        {"tipo_superficie": "  "},
        {"empresa_id": empresa.pk},
    ):
        respuesta = api.post("/api/canchas/", datos_cancha(ubicacion.pk, **extras), format="json")
        assert respuesta.status_code == 400


def test_propietario_admin_asignado_y_cajero_solo_lectura():
    propietario = usuario("dueno-roles@example.com")
    empresa = empresa_con_suscripcion(propietario, "Empresa Roles")
    asignada = sede(empresa, "Sede Asignada")
    no_asignada = sede(empresa, "Sede Privada")
    admin = usuario("admin-sede@example.com")
    membresia_admin = MembresiaEmpresa.objects.create(
        usuario=admin, empresa=empresa, rol=RolEmpresa.ADMINISTRADOR_SEDE
    )
    AsignacionSede.objects.create(sede=asignada, membresia=membresia_admin)
    cajero = usuario("cajero-sede@example.com")
    membresia_cajero = MembresiaEmpresa.objects.create(
        usuario=cajero, empresa=empresa, rol=RolEmpresa.CAJERO
    )
    AsignacionSede.objects.create(sede=asignada, membresia=membresia_cajero)
    cancha = crear_por_api(cliente(propietario), asignada.pk)

    api_admin = cliente(admin)
    creada_admin = api_admin.post(
        "/api/canchas/", datos_cancha(asignada.pk, nombre="Cancha Admin"), format="json"
    )
    assert creada_admin.status_code == 201
    assert api_admin.post(
        "/api/canchas/", datos_cancha(no_asignada.pk), format="json"
    ).status_code == 404
    assert api_admin.get(f"/api/canchas/{cancha['id']}/").status_code == 200

    api_cajero = cliente(cajero)
    assert api_cajero.get(f"/api/canchas/{cancha['id']}/").status_code == 200
    assert api_cajero.patch(
        f"/api/canchas/{cancha['id']}/", {"nombre": "No permitido"}, format="json"
    ).status_code == 403
    assert api_cajero.post(
        "/api/canchas/", datos_cancha(asignada.pk, nombre="No permitido"), format="json"
    ).status_code == 403


def test_aislamiento_entre_empresas_y_sede_en_filtro_no_autoriza():
    owner_a = usuario("owner-a-canchas@example.com")
    empresa_a = empresa_con_suscripcion(owner_a, "Empresa A")
    sede_a = sede(empresa_a, "Sede A")
    owner_b = usuario("owner-b-canchas@example.com")
    empresa_b = empresa_con_suscripcion(owner_b, "Empresa B")
    sede_b = sede(empresa_b, "Sede B")
    cancha_b = crear_por_api(cliente(owner_b), sede_b.pk)
    api_a = cliente(owner_a)

    respuesta = api_a.get(f"/api/canchas/?sede={sede_b.pk}")
    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 0
    assert api_a.get(f"/api/canchas/{cancha_b['id']}/").status_code == 404
    assert api_a.patch(
        f"/api/canchas/{cancha_b['id']}/", {"nombre": "Cambio"}, format="json"
    ).status_code == 404
    assert api_a.post(
        "/api/canchas/", datos_cancha(sede_b.pk), format="json"
    ).status_code == 404
    assert Cancha.objects.filter(sede=sede_a).count() == 0


def test_asignacion_sede_corrupta_de_otra_empresa_no_extiende_alcance():
    admin = usuario("admin-corrupto@example.com")
    empresa_a = empresa_con_suscripcion(usuario("owner-corrupto@example.com"), "Empresa A")
    empresa_b = empresa_con_suscripcion(usuario("owner-b-corrupto@example.com"), "Empresa B")
    sede_b = sede(empresa_b, "Sede B")
    membresia = MembresiaEmpresa.objects.create(
        usuario=admin, empresa=empresa_a, rol=RolEmpresa.ADMINISTRADOR_SEDE
    )
    AsignacionSede.objects.create(sede=sede_b, membresia=membresia)
    cancha_b = Cancha.objects.create(
        sede=sede_b, nombre="Privada", modalidad=7, tipo_superficie="Sintético"
    )

    api = cliente(admin)
    assert api.get(f"/api/canchas/{cancha_b.pk}/").status_code == 404
    assert api.get(f"/api/canchas/?sede={sede_b.pk}").data["count"] == 0
    assert api.post("/api/canchas/", datos_cancha(sede_b.pk), format="json").status_code == 404


def test_superadministrador_ve_y_administra_todas_las_empresas_con_auditoria():
    propietario = usuario("owner-global@example.com")
    empresa = empresa_con_suscripcion(propietario, "Empresa Global", limite=0)
    ubicacion = sede(empresa)
    superadmin = usuario("plataforma-canchas@example.com", superusuario=True)
    api = cliente(superadmin)

    creada = crear_por_api(api, ubicacion.pk)
    assert api.get(f"/api/canchas/{creada['id']}/").status_code == 200
    assert api.get("/api/canchas/").status_code == 200
    assert AccesoPlataforma.objects.filter(usuario=superadmin, accion="listar_canchas").exists()
    assert RegistroAuditoria.objects.filter(
        actor=superadmin, recurso="cancha", empresa=empresa
    ).count() == 2


def test_cuota_total_empresa_incluye_mantenimiento_e_inactivas_liberan_cupo():
    propietario = usuario("cuota-canchas@example.com")
    empresa = empresa_con_suscripcion(propietario, "Empresa Cuota", limite=1)
    sede_a = sede(empresa, "Sede A")
    sede_b = sede(empresa, "Sede B")
    api = cliente(propietario)
    cancha = crear_por_api(api, sede_a.pk)

    sin_confirmar = api.post(
        f"/api/canchas/{cancha['id']}/estado/",
        {"estado": "mantenimiento", "confirmar": False}, format="json",
    )
    assert sin_confirmar.status_code == 400

    mantenimiento = api.post(
        f"/api/canchas/{cancha['id']}/estado/",
        {"estado": "mantenimiento", "confirmar": True}, format="json",
    )
    assert mantenimiento.status_code == 200
    segunda = api.post("/api/canchas/", datos_cancha(sede_b.pk, nombre="Segunda"), format="json")
    assert segunda.status_code == 400

    inactiva = api.post(
        f"/api/canchas/{cancha['id']}/estado/",
        {"estado": "inactiva", "confirmar": True}, format="json",
    )
    assert inactiva.status_code == 200
    segunda = api.post("/api/canchas/", datos_cancha(sede_b.pk, nombre="Segunda"), format="json")
    assert segunda.status_code == 201
    reactivacion = api.post(
        f"/api/canchas/{cancha['id']}/estado/",
        {"estado": "activa", "confirmar": True}, format="json",
    )
    assert reactivacion.status_code == 400
    assert Cancha.objects.filter(
        sede__empresa=empresa,
        estado__in=[EstadoCancha.ACTIVA, EstadoCancha.MANTENIMIENTO],
    ).count() == 1


def test_cuota_cero_y_sin_limite():
    owner_cero = usuario("cuota-cero@example.com")
    empresa_cero = empresa_con_suscripcion(owner_cero, "Empresa Cero", limite=0)
    sede_cero = sede(empresa_cero)
    assert cliente(owner_cero).post(
        "/api/canchas/", datos_cancha(sede_cero.pk), format="json"
    ).status_code == 400

    owner_libre = usuario("cuota-libre@example.com")
    empresa_libre = empresa_con_suscripcion(owner_libre, "Empresa Libre", limite=None)
    sede_libre = sede(empresa_libre)
    api = cliente(owner_libre)
    assert crear_por_api(api, sede_libre.pk)
    assert crear_por_api(api, sede_libre.pk, nombre="Cancha Dos")


def test_imagenes_validan_firma_extension_tamano_y_retiro_logico(media_root):
    propietario = usuario("imagenes-canchas@example.com")
    empresa = empresa_con_suscripcion(propietario, "Empresa Imágenes")
    ubicacion = sede(empresa)
    api = cliente(propietario)
    cancha = crear_por_api(api, ubicacion.pk)

    primera = api.post(
        f"/api/canchas/{cancha['id']}/imagenes/",
        {"archivo": SimpleUploadedFile("primera.png", PNG, content_type="image/png")},
        format="multipart",
    )
    assert primera.status_code == 201, primera.data
    imagen_primera = primera.data["imagenes"][0]
    assert imagen_primera["principal"] is True
    primera_nombre = ImagenCancha.objects.get(pk=imagen_primera["id"]).archivo.name

    segunda = api.post(
        f"/api/canchas/{cancha['id']}/imagenes/",
        {"archivo": SimpleUploadedFile("segunda.jpg", b"\xff\xd8\xff\x00"), "orden": 2},
        format="multipart",
    )
    assert segunda.status_code == 201, segunda.data
    imagen_segunda = next(i for i in segunda.data["imagenes"] if i["id"] != imagen_primera["id"])
    segunda_nombre = ImagenCancha.objects.get(pk=imagen_segunda["id"]).archivo.name

    retirar = api.post(
        f"/api/canchas/{cancha['id']}/imagenes/{imagen_primera['id']}/retirar/",
        {"confirmar": True}, format="json",
    )
    assert retirar.status_code == 200
    objeto = Cancha.objects.get(pk=cancha["id"])
    assert objeto.imagen_principal.name == segunda_nombre
    assert not ImagenCancha.objects.get(pk=imagen_primera["id"]).activa
    assert (media_root / primera_nombre).exists()

    malos = (
        SimpleUploadedFile("tipo.txt", PNG, content_type="image/png"),
        SimpleUploadedFile("firma.png", b"no es una imagen"),
        SimpleUploadedFile("grande.png", PNG + b"x" * (5 * 1024 * 1024)),
    )
    for archivo in malos:
        respuesta = api.post(
            f"/api/canchas/{cancha['id']}/imagenes/", {"archivo": archivo}, format="multipart"
        )
        assert respuesta.status_code == 400
