from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.empresas.models import (
    AccesoPlataforma,
    Empresa,
    EstadoEmpresa,
    MembresiaEmpresa,
    RolEmpresa,
)
from apps.empresas.repositories.empresas import empresas_propietario
from apps.empresas.serializers import datos_empresa, responsables_empresa
from apps.empresas.services.auditoria import auditar


def datos_empresa_propietaria(empresa: Empresa) -> dict:
    return {
        **datos_empresa(empresa),
        "responsables": responsables_empresa(empresa),
        "cantidad_sedes": empresa.sedes.filter(activa=True).count(),
    }


@transaction.atomic
def crear_empresa(usuario: User, datos: dict) -> dict:
    if not usuario.is_authenticated or not usuario.is_active or usuario.is_superuser:
        raise PermissionDenied("Este perfil no puede registrar una empresa.")
    razon = datos.get("razon_social", "").strip()
    comercial = datos.get("nombre_comercial", "").strip()
    empresa = Empresa.objects.create(
        nombre=comercial or razon,
        activa=False,
        estado=EstadoEmpresa.PENDIENTE,
        razon_social=razon,
        nombre_comercial=comercial,
        ruc=datos.get("ruc", ""),
        descripcion=datos.get("descripcion", ""),
        correo_contacto=datos.get("correo_contacto", ""),
        telefono_contacto=datos.get("telefono_contacto", ""),
        direccion_administrativa=datos.get("direccion_administrativa", ""),
        logotipo=datos.get("logotipo"),
    )
    MembresiaEmpresa.objects.create(usuario=usuario, empresa=empresa, rol=RolEmpresa.DUENO)
    auditar(usuario, "crear", "empresa", empresa.pk, empresa, {"estado": empresa.estado})
    return datos_empresa_propietaria(empresa)


@transaction.atomic
def actualizar_empresa(usuario: User, identificador: int, datos: dict) -> dict:
    empresa = get_object_or_404(empresas_propietario(usuario).select_for_update(), pk=identificador)
    campos = (
        "razon_social", "nombre_comercial", "ruc", "descripcion", "correo_contacto",
        "telefono_contacto", "direccion_administrativa", "logotipo",
    )
    cambios = {campo: datos[campo] for campo in campos if campo in datos}
    for campo, valor in cambios.items():
        setattr(empresa, campo, valor.strip() if campo in {"razon_social", "nombre_comercial"} else valor)
    empresa.nombre = empresa.nombre_comercial or empresa.razon_social or empresa.nombre
    empresa.save(update_fields=[*cambios, "nombre"])
    auditar(usuario, "actualizar", "empresa", empresa.pk, empresa, {"campos": sorted(cambios)})
    return datos_empresa_propietaria(empresa)


def listar_empresas_propias(usuario: User, consulta: str = "") -> list[dict]:
    empresas = consulta_empresas_propias(usuario, consulta)
    return [datos_empresa_propietaria(empresa) for empresa in empresas]


def consulta_empresas_propias(usuario: User, consulta: str = "") -> QuerySet[Empresa]:
    empresas = empresas_propietario(usuario)
    if consulta:
        empresas = empresas.filter(
            Q(nombre__icontains=consulta) | Q(razon_social__icontains=consulta)
            | Q(nombre_comercial__icontains=consulta)
        )
    return empresas.order_by("id")


def consultar_empresa_propietaria(usuario: User, identificador: int) -> dict:
    empresa = get_object_or_404(empresas_propietario(usuario), pk=identificador)
    return datos_empresa_propietaria(empresa)


def modelo_empresa_propietaria(usuario: User, identificador: int) -> Empresa:
    return get_object_or_404(empresas_propietario(usuario), pk=identificador)


def datos_empresa_plataforma(empresa: Empresa) -> dict:
    suscripcion = getattr(empresa, "suscripcion", None)
    if suscripcion:
        from apps.suscripciones.services.suscripciones import estado_efectivo

        estado_suscripcion = estado_efectivo(suscripcion)
    else:
        estado_suscripcion = None
    return {
        **datos_empresa_propietaria(empresa),
        "suscripcion": (
            {"estado": estado_suscripcion, "plan": suscripcion.plan.nombre,
             "vencimiento": suscripcion.fecha_vencimiento}
            if suscripcion else None
        ),
    }


def consultar_empresa_plataforma(usuario: User, identificador: int) -> dict:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede consultar esta empresa.")
    empresa = get_object_or_404(
        Empresa.objects.select_related("suscripcion", "suscripcion__plan"), pk=identificador
    )
    AccesoPlataforma.objects.create(
        usuario=usuario, empresa=empresa, accion="consultar_empresa_fase_2"
    )
    return datos_empresa_plataforma(empresa)


def listar_empresas_plataforma(usuario: User, consulta: str = "", estado: str = "") -> list[dict]:
    empresas = consulta_empresas_plataforma(usuario, consulta, estado)
    return [datos_empresa_plataforma(empresa) for empresa in empresas]


def consulta_empresas_plataforma(
    usuario: User, consulta: str = "", estado: str = ""
) -> QuerySet[Empresa]:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede consultar todas las empresas.")
    empresas = Empresa.objects.select_related("suscripcion", "suscripcion__plan").all()
    if consulta:
        empresas = empresas.filter(
            Q(nombre__icontains=consulta) | Q(razon_social__icontains=consulta)
            | Q(ruc__icontains=consulta) | Q(nombre_comercial__icontains=consulta)
        )
    if estado in EstadoEmpresa.values:
        empresas = empresas.filter(estado=estado)
    AccesoPlataforma.objects.create(usuario=usuario, accion="listar_empresas_fase_2")
    return empresas.order_by("id")


@transaction.atomic
def cambiar_estado_empresa(usuario: User, identificador: int, nuevo_estado: str) -> dict:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede cambiar el estado.")
    if nuevo_estado not in EstadoEmpresa.values:
        raise ValidationError({"estado": "El estado solicitado no es válido."})
    empresa = get_object_or_404(Empresa.objects.select_for_update(), pk=identificador)
    transiciones = {
        EstadoEmpresa.PENDIENTE: {EstadoEmpresa.ACTIVA, EstadoEmpresa.RECHAZADA},
        EstadoEmpresa.RECHAZADA: {EstadoEmpresa.ACTIVA},
        EstadoEmpresa.ACTIVA: {EstadoEmpresa.SUSPENDIDA},
        EstadoEmpresa.SUSPENDIDA: {EstadoEmpresa.ACTIVA},
    }
    if nuevo_estado not in transiciones.get(empresa.estado, set()):
        raise ValidationError({"estado": "La empresa no puede pasar a ese estado."})
    if nuevo_estado == EstadoEmpresa.ACTIVA and not empresa.membresias.filter(
        rol=RolEmpresa.DUENO, activa=True, usuario__is_active=True
    ).exists():
        raise ValidationError({"estado": "La empresa necesita al menos un propietario activo."})
    anterior = empresa.estado
    empresa.estado = nuevo_estado
    empresa.activa = nuevo_estado == EstadoEmpresa.ACTIVA
    empresa.save(update_fields=["estado", "activa"])
    AccesoPlataforma.objects.create(
        usuario=usuario, empresa=empresa, accion=f"estado_empresa_{nuevo_estado}"
    )
    auditar(
        usuario, "cambiar_estado", "empresa", empresa.pk, empresa,
        {"anterior": anterior, "nuevo": nuevo_estado},
    )
    return datos_empresa_plataforma(empresa)
