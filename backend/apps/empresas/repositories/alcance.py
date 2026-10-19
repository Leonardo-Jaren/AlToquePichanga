from django.contrib.auth.models import User
from django.db.models import F, QuerySet

from apps.empresas.models import Empresa, MembresiaEmpresa, RolEmpresa
from apps.sedes.models import AsignacionSede, Sede


def membresias_autorizadas(usuario: User) -> QuerySet[MembresiaEmpresa]:
    return MembresiaEmpresa.objects.filter(
        usuario=usuario, activa=True, empresa__activa=True, usuario__is_active=True
    ).select_related("empresa")


def membresias_propietario_estado(usuario: User) -> QuerySet[MembresiaEmpresa]:
    return MembresiaEmpresa.objects.filter(
        usuario=usuario, rol=RolEmpresa.DUENO, activa=True, usuario__is_active=True
    ).exclude(empresa__activa=True).select_related("empresa")


def empresas_administrables(usuario: User) -> QuerySet[Empresa]:
    if not usuario.is_authenticated or not usuario.is_active:
        return Empresa.objects.none()
    if usuario.is_superuser:
        return Empresa.objects.all().order_by("id")
    return Empresa.objects.filter(
        id__in=membresias_autorizadas(usuario).filter(rol=RolEmpresa.DUENO).values("empresa_id")
    ).order_by("id")


def sedes_administrables(usuario: User) -> QuerySet[Sede]:
    if not usuario.is_authenticated or not usuario.is_active:
        return Sede.objects.none()
    if usuario.is_superuser:
        return Sede.objects.all().order_by("id")
    empresas = empresas_propietario_ids(usuario)
    asignaciones = AsignacionSede.objects.filter(
        activa=True,
        sede__empresa_id=F("membresia__empresa_id"),
        sede__empresa__activa=True,
        membresia__empresa__activa=True,
        membresia__usuario=usuario,
        membresia__activa=True,
        membresia__rol=RolEmpresa.ADMINISTRADOR_SEDE,
    ).values("sede_id")
    return Sede.objects.filter(empresa_id__in=empresas).union(
        Sede.objects.filter(id__in=asignaciones)
    ).order_by("id")


def empresas_propietario_ids(usuario: User):
    return MembresiaEmpresa.objects.filter(
        usuario=usuario, activa=True, rol=RolEmpresa.DUENO
    ).values("empresa_id")


def sedes_visibles(usuario: User) -> QuerySet[Sede]:
    if not usuario.is_authenticated or not usuario.is_active:
        return Sede.objects.none()
    if usuario.is_superuser:
        return Sede.objects.all().order_by("id")
    propias = Sede.objects.filter(empresa_id__in=empresas_propietario_ids(usuario))
    asignadas = Sede.objects.filter(
        empresa__activa=True,
        asignaciones__activa=True,
        asignaciones__membresia__empresa_id=F("empresa_id"),
        asignaciones__membresia__usuario=usuario,
        asignaciones__membresia__empresa__activa=True,
        asignaciones__membresia__activa=True,
        asignaciones__membresia__rol__in=[
            RolEmpresa.ADMINISTRADOR_SEDE, RolEmpresa.CAJERO,
        ],
    )
    return (propias | asignadas).distinct().order_by("id")


def sede_administrable(usuario: User, sede_id: int) -> bool:
    if not usuario.is_authenticated or not usuario.is_active:
        return False
    if usuario.is_superuser:
        return Sede.objects.filter(pk=sede_id).exists()
    propia = Sede.objects.filter(
        pk=sede_id, empresa_id__in=empresas_propietario_ids(usuario)
    ).exists()
    if propia:
        return True
    return AsignacionSede.objects.filter(
        sede_id=sede_id, activa=True, membresia__usuario=usuario,
        sede__empresa_id=F("membresia__empresa_id"),
        sede__empresa__activa=True,
        membresia__empresa__activa=True, membresia__activa=True,
        membresia__rol=RolEmpresa.ADMINISTRADOR_SEDE,
    ).exists()
