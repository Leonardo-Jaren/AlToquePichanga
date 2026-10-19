from django.contrib.auth.models import User
from django.db.models import QuerySet

from apps.empresas.models import Empresa, MembresiaEmpresa, RolEmpresa


def empresas_propietario(usuario: User) -> QuerySet[Empresa]:
    if not usuario.is_authenticated or not usuario.is_active or usuario.is_superuser:
        return Empresa.objects.none()
    ids = MembresiaEmpresa.objects.filter(
        usuario=usuario, activa=True, rol=RolEmpresa.DUENO
    ).values("empresa_id")
    return Empresa.objects.filter(id__in=ids).order_by("id")


def membresias_empresa(empresa: Empresa) -> QuerySet[MembresiaEmpresa]:
    return MembresiaEmpresa.objects.filter(empresa=empresa, activa=True).select_related(
        "usuario", "usuario__perfil"
    ).order_by("rol", "usuario__first_name", "usuario__id")
