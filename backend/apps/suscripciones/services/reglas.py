from calendar import monthrange
from datetime import date, timedelta

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.empresas.models import (
    Empresa,
    InvitacionEmpleado,
    MembresiaEmpresa,
    RolEmpresa,
)
from apps.suscripciones.models import (
    ConfiguracionSuscripcion,
    EstadoSuscripcion,
    FrecuenciaSuscripcion,
    SuscripcionEmpresa,
)
from apps.usuarios.models import PerfilUsuario

MESES_POR_FRECUENCIA = {
    FrecuenciaSuscripcion.MENSUAL: 1,
    FrecuenciaSuscripcion.TRIMESTRAL: 3,
    FrecuenciaSuscripcion.SEMESTRAL: 6,
    FrecuenciaSuscripcion.ANUAL: 12,
}


def agregar_meses(fecha: date, meses: int) -> date:
    indice = fecha.year * 12 + fecha.month - 1 + meses
    año, mes = divmod(indice, 12)
    mes += 1
    return date(año, mes, min(fecha.day, monthrange(año, mes)[1]))


def calcular_vencimiento(inicio: date, frecuencia: str) -> date:
    meses = MESES_POR_FRECUENCIA.get(frecuencia)
    if meses is None:
        raise ValidationError({"frecuencia": "La periodicidad no es válida."})
    return agregar_meses(inicio, meses) - timedelta(days=1)


def dias_gracia_suscripcion() -> int:
    return ConfiguracionSuscripcion.objects.filter(pk=1).values_list(
        "dias_gracia", flat=True
    ).first() or 0


def suscripcion_vigente(suscripcion: SuscripcionEmpresa, hoy: date) -> bool:
    return bool(
        suscripcion.estado == EstadoSuscripcion.ACTIVA
        and suscripcion.fecha_vencimiento
        and hoy <= suscripcion.fecha_vencimiento + timedelta(days=dias_gracia_suscripcion())
    )


def suscripcion_operativa(empresa: Empresa, hoy: date | None = None) -> bool:
    suscripcion = SuscripcionEmpresa.objects.filter(empresa=empresa).first()
    if not empresa.activa or empresa.estado != "activa" or not suscripcion:
        return False
    hoy = hoy or timezone.localdate()
    return suscripcion_vigente(suscripcion, hoy)


@transaction.atomic
def empresa_con_cupo(identificador: int, tipo: str, usuario: User | None = None) -> Empresa:
    empresa = get_object_or_404(Empresa.objects.select_for_update(), pk=identificador)
    suscripcion = SuscripcionEmpresa.objects.select_for_update().select_related("plan").filter(
        empresa=empresa
    ).first()
    if (not empresa.activa or empresa.estado != "activa" or not suscripcion
            or not suscripcion_vigente(suscripcion, timezone.localdate())):
        raise PermissionDenied(
            "La empresa necesita una suscripción vigente y aprobación de plataforma."
        )
    if tipo == "sede":
        limite = suscripcion.plan.maximo_sedes
        usado = empresa.sedes.filter(activa=True).count()
    elif tipo == "empleado":
        limite = suscripcion.plan.maximo_empleados
        usado = MembresiaEmpresa.objects.filter(
            empresa=empresa, activa=True,
            rol__in=[RolEmpresa.ADMINISTRADOR_SEDE, RolEmpresa.CAJERO],
            usuario__is_active=True,
        ).values("usuario_id").distinct().count()
        if usuario and MembresiaEmpresa.objects.filter(
            empresa=empresa, usuario=usuario, activa=True,
            rol__in=[RolEmpresa.ADMINISTRADOR_SEDE, RolEmpresa.CAJERO],
        ).exists():
            return empresa
        invitaciones = InvitacionEmpleado.objects.filter(
            empresa=empresa, aceptada_en__isnull=True, cancelada_en__isnull=True,
            rol__in=[RolEmpresa.ADMINISTRADOR_SEDE, RolEmpresa.CAJERO],
            vence_en__gt=timezone.now(),
        )
        if usuario:
            perfil = PerfilUsuario.objects.filter(usuario=usuario).values_list("correo", flat=True).first()
            if perfil:
                invitaciones = invitaciones.exclude(correo__iexact=perfil)
        usado += invitaciones.annotate(correo_normalizado=Lower("correo")).values(
            "correo_normalizado"
        ).distinct().count()
    elif tipo == "cancha":
        from apps.canchas.models import Cancha, EstadoCancha

        limite = suscripcion.plan.maximo_canchas
        usado = Cancha.objects.filter(
            sede__empresa_id=empresa.pk,
            estado__in=[EstadoCancha.ACTIVA, EstadoCancha.MANTENIMIENTO],
        ).count()
    else:
        raise ValueError("Tipo de límite desconocido.")
    if limite is not None and usado >= limite:
        raise ValidationError({
            "limite": f"El plan alcanzó su límite de {limite} {tipo}(s) activos."
        })
    return empresa
