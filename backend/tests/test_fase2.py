import re
from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.empresas.models import (
    AccesoPlataforma,
    Empresa,
    EstadoEmpresa,
    InvitacionEmpleado,
    MembresiaEmpresa,
    RegistroAuditoria,
    RolEmpresa,
)
from apps.empresas.services.personal import aceptar_invitacion
from apps.sedes.models import AsignacionSede, Sede
from apps.suscripciones.models import (
    EstadoSolicitud,
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    PagoSuscripcion,
    PeriodoSuscripcion,
    PlanSuscripcion,
    SolicitudSuscripcion,
    SuscripcionEmpresa,
)
from apps.usuarios.models import CorreoPendiente, PerfilUsuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def crear_usuario():
    def crear(correo: str, *, superusuario: bool = False) -> User:
        usuario = User.objects.create_user(
            username=correo, email=correo, password="Pichanga-fuerte-927!",
            is_superuser=superusuario, is_staff=superusuario,
        )
        PerfilUsuario.objects.create(usuario=usuario, correo=correo)
        return usuario
    return crear


def cliente(usuario: User) -> APIClient:
    api = APIClient()
    api.force_authenticate(usuario)
    return api


def crear_empresa(usuario: User, nombre: str, *, estado: str = EstadoEmpresa.ACTIVA) -> Empresa:
    empresa = Empresa.objects.create(
        nombre=nombre, razon_social=nombre, estado=estado,
        activa=estado == EstadoEmpresa.ACTIVA,
    )
    MembresiaEmpresa.objects.create(usuario=usuario, empresa=empresa, rol=RolEmpresa.DUENO)
    return empresa


def crear_plan(**cambios) -> PlanSuscripcion:
    datos = {
        "nombre": "Plan de prueba", "precio": Decimal("120.00"), "moneda": "PEN",
        "frecuencia": FrecuenciaSuscripcion.MENSUAL, "maximo_sedes": None,
        "maximo_empleados": None,
    }
    datos.update(cambios)
    return PlanSuscripcion.objects.create(**datos)


def activar_suscripcion(empresa: Empresa, plan: PlanSuscripcion) -> SuscripcionEmpresa:
    hoy = timezone.localdate()
    return SuscripcionEmpresa.objects.create(
        empresa=empresa, plan=plan, estado=EstadoSuscripcion.ACTIVA,
        fecha_inicio=hoy, fecha_vencimiento=hoy + timedelta(days=30),
        importe_acordado=plan.precio, moneda_acordada=plan.moneda,
        frecuencia_acordada=plan.frecuencia,
    )


def crear_sede(empresa: Empresa, nombre: str = "Sede Centro") -> Sede:
    return Sede.objects.create(empresa=empresa, nombre=nombre, direccion="Av. Principal 123")


def test_registro_empresa_queda_pendiente_y_solo_el_dueno_la_consulta(
    crear_usuario,
):
    dueno = crear_usuario("dueno@example.com")
    otra_persona = crear_usuario("otra@example.com")
    api = cliente(dueno)

    alta = api.post("/api/empresas/", {
        "razon_social": "Complejos Huánuco", "nombre_comercial": "Huánuco Fútbol",
        "ruc": "20123456789",
    }, format="json")

    assert alta.status_code == 201
    empresa = Empresa.objects.get(pk=alta.data["id"])
    assert empresa.estado == EstadoEmpresa.PENDIENTE
    assert empresa.activa is False
    assert MembresiaEmpresa.objects.filter(
        empresa=empresa, usuario=dueno, rol=RolEmpresa.DUENO, activa=True,
    ).exists()
    co_dueno = crear_usuario("co-dueno@example.com")
    MembresiaEmpresa.objects.create(
        usuario=co_dueno, empresa=empresa, rol=RolEmpresa.DUENO,
    )
    crear_empresa(dueno, "Otra empresa autorizada", estado=EstadoEmpresa.PENDIENTE)
    assert api.get(f"/api/empresas/administradas/{empresa.pk}/").data["estado"] == "pendiente"
    assert api.get("/api/empresas/administradas/").data["count"] == 2
    assert cliente(co_dueno).get(
        f"/api/empresas/administradas/{empresa.pk}/"
    ).status_code == 200
    assert cliente(otra_persona).get(
        f"/api/empresas/administradas/{empresa.pk}/"
    ).status_code == 404
    elevacion = api.post("/api/empresas/", {
        "razon_social": "No autorizado", "estado": "activa", "activa": True,
    }, format="json")
    assert elevacion.status_code == 400


def test_superadministrador_filtra_aprueba_y_audita_empresas(crear_usuario):
    dueno = crear_usuario("pendiente@example.com")
    superadmin = crear_usuario("plataforma@example.com", superusuario=True)
    empresa = crear_empresa(dueno, "Pendiente", estado=EstadoEmpresa.PENDIENTE)
    api_super = cliente(superadmin)

    listado = api_super.get("/api/empresas/plataforma/?estado=pendiente&page_size=5")
    assert listado.status_code == 200
    assert listado.data["count"] == 1
    assert listado.data["results"][0]["responsables"][0]["correo"] == dueno.email
    assert cliente(dueno).patch(
        f"/api/empresas/plataforma/{empresa.pk}/", {"estado": "activa"}, format="json"
    ).status_code == 403

    aprobacion = api_super.patch(
        f"/api/empresas/plataforma/{empresa.pk}/", {"estado": "activa"}, format="json"
    )
    empresa.refresh_from_db()
    assert aprobacion.status_code == 200
    assert empresa.activa and empresa.estado == EstadoEmpresa.ACTIVA
    assert AccesoPlataforma.objects.filter(usuario=superadmin, empresa=empresa).exists()
    assert RegistroAuditoria.objects.filter(
        actor=superadmin, empresa=empresa, accion="cambiar_estado", recurso="empresa",
    ).exists()


def test_rechazo_y_suspension_no_conceden_estado_comercial(crear_usuario):
    dueno = crear_usuario("estados-owner@example.com")
    superadmin = crear_usuario("estados-admin@example.com", superusuario=True)
    pendiente = crear_empresa(dueno, "Aún no aprobada", estado=EstadoEmpresa.PENDIENTE)
    api_super = cliente(superadmin)

    rechazo = api_super.patch(
        f"/api/empresas/plataforma/{pendiente.pk}/", {"estado": "rechazada"}, format="json"
    )
    assert rechazo.status_code == 200
    pendiente.refresh_from_db()
    assert pendiente.estado == EstadoEmpresa.RECHAZADA and not pendiente.activa

    aprobada = api_super.patch(
        f"/api/empresas/plataforma/{pendiente.pk}/", {"estado": "activa"}, format="json"
    )
    assert aprobada.status_code == 200
    api_super.patch(
        f"/api/empresas/plataforma/{pendiente.pk}/", {"estado": "suspendida"}, format="json"
    )
    pendiente.refresh_from_db()
    assert pendiente.estado == EstadoEmpresa.SUSPENDIDA and not pendiente.activa
    assert cliente(dueno).get("/api/empresas/administradas/").data["count"] == 1


def test_sedes_aisladas_no_se_transfieren_y_respetan_el_limite(crear_usuario):
    dueno = crear_usuario("sede-owner@example.com")
    ajeno = crear_usuario("sede-other@example.com")
    empresa = crear_empresa(dueno, "Empresa Uno")
    otra_empresa = crear_empresa(ajeno, "Empresa Dos")
    plan = crear_plan(maximo_sedes=1)
    activar_suscripcion(empresa, plan)
    api = cliente(dueno)

    alta = api.post("/api/sedes/", {
        "empresa_id": empresa.pk, "nombre": "Centro", "direccion": "Jr. Lima 10",
        "latitud": -9.93, "longitud": -76.24, "horario_general": {"lunes": "08:00-22:00"},
    }, format="json")
    assert alta.status_code == 201
    sede_id = alta.data["id"]
    cambio = api.patch(f"/api/sedes/{sede_id}/", {"distrito": "Amarilis"}, format="json")
    assert cambio.status_code == 200 and cambio.data["distrito"] == "Amarilis"
    assert api.patch(f"/api/sedes/{sede_id}/", {
        "empresa_id": otra_empresa.pk,
    }, format="json").status_code == 400
    assert cliente(ajeno).get(f"/api/sedes/{sede_id}/").status_code == 404
    segunda = api.post("/api/sedes/", {
        "empresa_id": empresa.pk, "nombre": "Segunda", "direccion": "Otra dirección",
    }, format="json")
    assert segunda.status_code == 400
    assert Sede.objects.filter(empresa=empresa).count() == 1


def test_administrador_sede_solo_ve_y_edita_sedes_asignadas(crear_usuario):
    dueno = crear_usuario("sedes-owner@example.com")
    administrador = crear_usuario("admin-sede@example.com")
    empresa = crear_empresa(dueno, "Complejos Uno")
    activar_suscripcion(empresa, crear_plan())
    asignada = crear_sede(empresa, "Sede autorizada")
    ajena = crear_sede(empresa, "Sede sin asignar")
    membresia = MembresiaEmpresa.objects.create(
        usuario=administrador, empresa=empresa, rol=RolEmpresa.ADMINISTRADOR_SEDE,
    )
    AsignacionSede.objects.create(sede=asignada, membresia=membresia)
    api = cliente(administrador)

    filas = api.get("/api/sedes/").data
    assert [fila["id"] for fila in filas] == [asignada.pk]
    assert api.patch(f"/api/sedes/{asignada.pk}/", {"nombre": "Actualizada"}, format="json").status_code == 200
    assert api.get(f"/api/sedes/{ajena.pk}/").status_code == 404
    assert api.patch(f"/api/sedes/{ajena.pk}/", {"nombre": "Intrusión"}, format="json").status_code == 404
    assert api.get(f"/api/empresas/administradas/{empresa.pk}/personal/").status_code == 404


def test_asignacion_revocacion_y_proteccion_del_ultimo_dueno(crear_usuario):
    dueno = crear_usuario("dueno-equipo@example.com")
    empleado = crear_usuario("cajero@example.com")
    empresa = crear_empresa(dueno, "Equipo")
    activar_suscripcion(empresa, crear_plan(maximo_empleados=2))
    sede = crear_sede(empresa)
    api = cliente(dueno)

    asignacion = api.post(f"/api/empresas/administradas/{empresa.pk}/personal/", {
        "correo": empleado.email, "rol": "cajero", "sedes": [sede.pk],
    }, format="json")
    assert asignacion.status_code == 200
    membresia = MembresiaEmpresa.objects.get(usuario=empleado, empresa=empresa)
    assert membresia.rol == RolEmpresa.CAJERO
    assert list(membresia.sedes_asignadas.filter(activa=True).values_list("sede_id", flat=True)) == [sede.pk]
    dueno_ajeno = crear_usuario("otra-empresa@example.com")
    empresa_ajena = crear_empresa(dueno_ajeno, "Otra empresa")
    sede_ajena = crear_sede(empresa_ajena, "Sede ajena")
    sede_cruzada = api.post(f"/api/empresas/administradas/{empresa.pk}/personal/", {
        "correo": "invitado@example.com", "rol": "cajero", "sedes": [sede_ajena.pk],
    }, format="json")
    assert sede_cruzada.status_code == 400
    elevacion = api.post(f"/api/empresas/administradas/{empresa.pk}/personal/", {
        "correo": "cajero@example.com", "rol": "superadministrador", "sedes": [],
    }, format="json")
    assert elevacion.status_code == 400
    assert api.post(
        f"/api/empresas/administradas/{empresa.pk}/personal/{membresia.pk}/revocar/",
        {"confirmar": True}, format="json",
    ).data["activa"] is False
    assert cliente(empleado).get("/api/sedes/").data == []
    propietario = MembresiaEmpresa.objects.get(usuario=dueno, empresa=empresa)
    ultimo = api.post(
        f"/api/empresas/administradas/{empresa.pk}/personal/{propietario.pk}/revocar/",
        {"confirmar": True}, format="json",
    )
    assert ultimo.status_code == 400
    propietario.refresh_from_db()
    assert propietario.activa


def test_invitacion_secreta_se_acepta_una_vez_al_registrar(crear_usuario):
    dueno = crear_usuario("invita@example.com")
    empresa = crear_empresa(dueno, "Invitaciones")
    activar_suscripcion(empresa, crear_plan(maximo_empleados=1))
    sede = crear_sede(empresa)
    respuesta = cliente(dueno).post(f"/api/empresas/administradas/{empresa.pk}/personal/", {
        "correo": "nuevo-empleado@example.com", "rol": "cajero", "sedes": [sede.pk],
    }, format="json")
    assert respuesta.status_code == 201
    invitacion = InvitacionEmpleado.objects.get(pk=respuesta.data["id"])
    correo = CorreoPendiente.objects.get(destinatario=invitacion.correo)
    token = re.search(r"#invitacion=([A-Za-z0-9_-]+)", correo.contenido).group(1)
    assert token not in invitacion.token_hash
    assert len(invitacion.token_hash) == 64

    registro = APIClient().post("/api/auth/registro/", {
        "correo": invitacion.correo, "nombre": "Nuevo", "apellidos": "Empleado",
        "contrasena": "Pichanga-fuerte-927!", "invitacion": token,
    }, format="json")
    assert registro.status_code == 201
    empleado = User.objects.get(email=invitacion.correo)
    assert MembresiaEmpresa.objects.filter(
        usuario=empleado, empresa=empresa, rol=RolEmpresa.CAJERO, activa=True,
        sedes_asignadas__sede=sede, sedes_asignadas__activa=True,
    ).exists()
    invitacion.refresh_from_db()
    assert invitacion.aceptada_en is not None
    repetir = cliente(empleado).post(
        "/api/empresas/invitaciones/aceptar/", {"token": token}, format="json",
    )
    assert repetir.status_code == 400


def test_invitacion_vencida_no_asigna_ningun_rol(crear_usuario):
    dueno = crear_usuario("invita-vencida@example.com")
    empresa = crear_empresa(dueno, "Invitación vencida")
    activar_suscripcion(empresa, crear_plan(maximo_empleados=1))
    sede = crear_sede(empresa)
    respuesta = cliente(dueno).post(f"/api/empresas/administradas/{empresa.pk}/personal/", {
        "correo": "vencido@example.com", "rol": "cajero", "sedes": [sede.pk],
    }, format="json")
    invitacion = InvitacionEmpleado.objects.get(pk=respuesta.data["id"])
    contenido = CorreoPendiente.objects.get(destinatario=invitacion.correo).contenido
    token = re.search(r"#invitacion=([A-Za-z0-9_-]+)", contenido).group(1)
    invitacion.vence_en = timezone.now() - timedelta(minutes=1)
    invitacion.save(update_fields=["vence_en"])
    nueva = cliente(dueno).post(f"/api/empresas/administradas/{empresa.pk}/personal/", {
        "correo": invitacion.correo, "rol": "cajero", "sedes": [sede.pk],
    }, format="json")
    invitacion.refresh_from_db()
    assert nueva.status_code == 201 and nueva.data["id"] != invitacion.pk
    assert invitacion.cancelada_en is not None
    reemplazo = InvitacionEmpleado.objects.get(pk=nueva.data["id"])
    contenido_nuevo = CorreoPendiente.objects.filter(
        destinatario=invitacion.correo
    ).order_by("id").last().contenido
    token_nuevo = re.search(r"#invitacion=([A-Za-z0-9_-]+)", contenido_nuevo).group(1)
    reemplazo.vence_en = timezone.now() - timedelta(minutes=1)
    reemplazo.save(update_fields=["vence_en"])
    candidato = crear_usuario(invitacion.correo)

    with pytest.raises(ValidationError):
        aceptar_invitacion(candidato, token)
    with pytest.raises(ValidationError):
        aceptar_invitacion(candidato, token_nuevo)
    assert not MembresiaEmpresa.objects.filter(usuario=candidato, empresa=empresa).exists()


def test_solicitud_no_activa_y_aprobacion_guarda_importe_historico(crear_usuario):
    dueno = crear_usuario("saas-owner@example.com")
    superadmin = crear_usuario("saas-admin@example.com", superusuario=True)
    empresa = crear_empresa(dueno, "SaaS", estado=EstadoEmpresa.PENDIENTE)
    api_super = cliente(superadmin)
    plan = api_super.post("/api/plataforma/planes/", {
        "nombre": "Inicial", "precio": "120.00", "moneda": "PEN",
        "frecuencia": "mensual", "maximo_sedes": 2, "maximo_empleados": 5,
    }, format="json")
    assert plan.status_code == 201
    solicitud = cliente(dueno).post(
        f"/api/empresas/administradas/{empresa.pk}/suscripcion/",
        {"plan_id": plan.data["id"], "medio_declarado": "transferencia"}, format="json",
    )
    assert solicitud.status_code == 201
    assert not SuscripcionEmpresa.objects.filter(empresa=empresa).exists()
    assert cliente(dueno).post(
        f"/api/plataforma/empresas/{empresa.pk}/suscripcion/estado/",
        {"estado": "activa"}, format="json",
    ).status_code == 403

    importe_incorrecto = api_super.post(
        f"/api/plataforma/solicitudes/{solicitud.data['id']}/resolver/",
        {"aprobar": True, "importe_verificado": "119.00"}, format="json",
    )
    assert importe_incorrecto.status_code == 400
    assert not SuscripcionEmpresa.objects.filter(empresa=empresa).exists()

    resuelta = api_super.post(
        f"/api/plataforma/solicitudes/{solicitud.data['id']}/resolver/",
        {"aprobar": True, "importe_verificado": "120.00", "referencia_verificada": "OP-1"},
        format="json",
    )
    assert resuelta.status_code == 200
    assert SolicitudSuscripcion.objects.get(pk=solicitud.data["id"]).estado == EstadoSolicitud.APROBADA
    periodo = PeriodoSuscripcion.objects.get()
    assert periodo.importe_acordado == Decimal("120.00")
    assert PagoSuscripcion.objects.get().confirmado_por == superadmin
    api_super.patch(f"/api/plataforma/planes/{plan.data['id']}/", {
        "precio": "180.00",
    }, format="json")
    periodo.refresh_from_db()
    assert periodo.importe_acordado == Decimal("120.00")
    empresa.refresh_from_db()
    assert empresa.estado == EstadoEmpresa.PENDIENTE and not empresa.activa
    assert not hasattr(PagoSuscripcion.objects.get(), "reserva_id")
