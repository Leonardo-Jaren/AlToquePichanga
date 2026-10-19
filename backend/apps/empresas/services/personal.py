import hashlib
import secrets
from datetime import timedelta
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.empresas.models import (
    Empresa,
    InvitacionEmpleado,
    MembresiaEmpresa,
    RolEmpresa,
)
from apps.empresas.repositories.empresas import empresas_propietario
from apps.empresas.services.auditoria import auditar
from apps.sedes.models import AsignacionSede, Sede
from apps.suscripciones.services.reglas import empresa_con_cupo
from apps.usuarios.models import CorreoPendiente, PerfilUsuario
from apps.usuarios.repositories.usuarios import usuario_por_correo

ROLES_PERSONAL = {RolEmpresa.DUENO, RolEmpresa.ADMINISTRADOR_SEDE, RolEmpresa.CAJERO}
ROLES_CON_SEDE = {RolEmpresa.ADMINISTRADOR_SEDE, RolEmpresa.CAJERO}


def _empresa_propietaria(usuario: User, identificador: int, bloquear: bool = False) -> Empresa:
    empresas = empresas_propietario(usuario)
    if bloquear:
        empresas = empresas.select_for_update()
    return get_object_or_404(empresas, pk=identificador)


def _validar_sedes(empresa: Empresa, ids: list[int], rol: str) -> list[Sede]:
    if rol == RolEmpresa.DUENO and ids:
        raise ValidationError({"sedes": "El rol de dueño administra la empresa completa."})
    if rol in ROLES_CON_SEDE and not ids:
        raise ValidationError({"sedes": "Asigna al menos una sede para este rol."})
    sedes = list(Sede.objects.filter(
        empresa=empresa, activa=True, pk__in=set(ids)
    ).order_by("id"))
    if len(sedes) != len(set(ids)):
        raise ValidationError({"sedes": "Todas las sedes deben pertenecer a esta empresa."})
    return sedes


def _reemplazar_sedes(membresia: MembresiaEmpresa, sedes: list[Sede]) -> None:
    ids = [sede.pk for sede in sedes]
    AsignacionSede.objects.filter(membresia=membresia).exclude(sede_id__in=ids).update(activa=False)
    for sede in sedes:
        AsignacionSede.objects.update_or_create(
            membresia=membresia, sede=sede, defaults={"activa": True}
        )


def _asignar_usuario(
    empresa: Empresa, objetivo: User, rol: str, sedes: list[Sede]
) -> MembresiaEmpresa:
    if objetivo.is_superuser:
        raise ValidationError({"correo": "Una cuenta de plataforma no se asigna como empleado."})
    dueno_activo = MembresiaEmpresa.objects.filter(
        empresa=empresa, usuario=objetivo, activa=True, rol=RolEmpresa.DUENO
    ).exists()
    if dueno_activo and rol != RolEmpresa.DUENO:
        raise ValidationError({"rol": "Una persona propietaria conserva sus permisos de empresa."})
    if rol in ROLES_CON_SEDE:
        empresa_con_cupo(empresa.pk, "empleado", objetivo)
    memberships = MembresiaEmpresa.objects.filter(empresa=empresa, usuario=objetivo)
    anteriores = memberships.filter(rol__in=ROLES_CON_SEDE - {rol}, activa=True)
    ids_anteriores = list(anteriores.values_list("id", flat=True))
    anteriores.update(activa=False)
    AsignacionSede.objects.filter(membresia_id__in=ids_anteriores).update(activa=False)
    membership, _ = MembresiaEmpresa.objects.get_or_create(
        empresa=empresa, usuario=objetivo, rol=rol
    )
    if not membership.activa:
        membership.activa = True
        membership.save(update_fields=["activa"])
    _reemplazar_sedes(membership, sedes)
    return membership


def _datos_membresia(membresia: MembresiaEmpresa) -> dict:
    perfil = PerfilUsuario.objects.filter(usuario=membresia.usuario).first()
    return {
        "id": membresia.pk, "usuario_id": membresia.usuario_id,
        "correo": perfil.correo if perfil else "",
        "nombre": membresia.usuario.get_full_name(), "rol": membresia.rol,
        "activa": membresia.activa,
        "sedes": list(membresia.sedes_asignadas.filter(activa=True).values_list(
            "sede_id", flat=True
        )),
    }


def listar_personal(usuario: User, identificador: int) -> dict:
    empresa = _empresa_propietaria(usuario, identificador)
    personal = MembresiaEmpresa.objects.filter(empresa=empresa).select_related(
        "usuario"
    ).order_by("rol", "usuario_id")
    invitaciones = InvitacionEmpleado.objects.filter(
        empresa=empresa, aceptada_en__isnull=True, cancelada_en__isnull=True
    ).order_by("-creada_en")
    ahora = timezone.now()
    return {
        "personal": [_datos_membresia(m) for m in personal],
        "invitaciones": [{
            "id": inv.pk, "correo": inv.correo, "rol": inv.rol,
            "estado": "expirada" if inv.vence_en <= ahora else "pendiente",
            "vence_en": inv.vence_en, "sedes": list(inv.sedes.values_list("id", flat=True)),
        } for inv in invitaciones],
    }


@transaction.atomic
def asignar_personal(usuario: User, identificador: int, datos: dict) -> dict:
    empresa = _empresa_propietaria(usuario, identificador, bloquear=True)
    correo = datos["correo"].strip().lower()
    rol = datos["rol"]
    if rol not in ROLES_PERSONAL:
        raise ValidationError({"rol": "El rol solicitado no está disponible."})
    sedes = _validar_sedes(empresa, datos.get("sedes", []), rol)
    objetivo = usuario_por_correo(correo)
    if not objetivo:
        raise ValidationError({"correo": "No hay una cuenta registrada con ese correo. Envía una invitación."})
    existentes = MembresiaEmpresa.objects.filter(
        empresa=empresa, usuario=objetivo, activa=True, rol=RolEmpresa.DUENO
    ).exists()
    if existentes and rol != RolEmpresa.DUENO:
        raise ValidationError({"rol": "La persona ya es propietaria de esta empresa."})
    membership = _asignar_usuario(empresa, objetivo, rol, sedes)
    auditar(
        usuario, "asignar", "membresia", membership.pk, empresa,
        {"rol": rol, "sedes": [s.pk for s in sedes]},
    )
    return _datos_membresia(membership)


@transaction.atomic
def invitar_personal(usuario: User, identificador: int, datos: dict) -> dict:
    empresa = _empresa_propietaria(usuario, identificador, bloquear=True)
    correo = datos["correo"].strip().lower()
    rol = datos["rol"]
    if rol not in ROLES_PERSONAL:
        raise ValidationError({"rol": "El rol solicitado no está disponible."})
    sedes = _validar_sedes(empresa, datos.get("sedes", []), rol)
    objetivo = usuario_por_correo(correo)
    if objetivo:
        membership = _asignar_usuario(empresa, objetivo, rol, sedes)
        auditar(usuario, "asignar", "membresia", membership.pk, empresa, {"rol": rol})
        return {"tipo": "asignado", **_datos_membresia(membership)}
    if rol in ROLES_CON_SEDE:
        empresa_con_cupo(empresa.pk, "empleado")
    token = secrets.token_urlsafe(32)
    ahora = timezone.now()
    vencidas = InvitacionEmpleado.objects.select_for_update().filter(
        empresa=empresa, correo__iexact=correo, aceptada_en__isnull=True,
        cancelada_en__isnull=True, vence_en__lte=ahora,
    )
    for anterior in vencidas:
        anterior.cancelada_en = ahora
        anterior.save(update_fields=["cancelada_en"])
        auditar(
            usuario, "expirar", "invitacion_empleado", anterior.pk, empresa,
            {"correo": correo},
        )
    try:
        with transaction.atomic():
            invitacion = InvitacionEmpleado.objects.create(
                empresa=empresa, correo=correo, rol=rol, creador=usuario,
                token_hash=hashlib.sha256(token.encode()).hexdigest(),
                vence_en=timezone.now() + timedelta(days=settings.INVITACION_DIAS_VIGENCIA),
            )
            invitacion.sedes.set(sedes)
    except IntegrityError:
        raise ValidationError({"correo": "Ya existe una invitación pendiente para ese correo."}) from None
    enlace = f"{settings.FRONTEND_URL}/registro#invitacion={quote(token)}"
    CorreoPendiente.objects.create(
        destinatario=correo,
        asunto=f"Invitación para {empresa.nombre_visible}",
        contenido=(
            f"Te invitaron a {empresa.nombre_visible} con el rol {rol}. "
            f"Crea tu cuenta desde este enlace: {enlace}. "
            f"El enlace vence en {settings.INVITACION_DIAS_VIGENCIA} días y solo se usa una vez."
        ),
    )
    auditar(
        usuario, "invitar", "invitacion_empleado", invitacion.pk, empresa,
        {"rol": rol, "sedes": [s.pk for s in sedes]},
    )
    return {"tipo": "invitacion", "id": invitacion.pk, "estado": "pendiente"}


@transaction.atomic
def revocar_personal(usuario: User, identificador: int, membresia_id: int) -> dict:
    empresa = _empresa_propietaria(usuario, identificador, bloquear=True)
    membresia = get_object_or_404(
        MembresiaEmpresa.objects.select_for_update(),
        pk=membresia_id, empresa=empresa, activa=True,
    )
    if membresia.rol == RolEmpresa.DUENO:
        propietarios = MembresiaEmpresa.objects.filter(
            empresa=empresa, rol=RolEmpresa.DUENO, activa=True, usuario__is_active=True
        ).count()
        if propietarios <= 1:
            raise ValidationError({"membresia": "La empresa necesita conservar al menos un propietario."})
    membresia.activa = False
    membresia.save(update_fields=["activa"])
    membresia.sedes_asignadas.filter(activa=True).update(activa=False)
    auditar(usuario, "revocar", "membresia", membresia.pk, empresa, {"rol": membresia.rol})
    return {"id": membresia.pk, "activa": False}


@transaction.atomic
def revocar_invitacion(usuario: User, identificador: int, invitacion_id: int) -> dict:
    empresa = _empresa_propietaria(usuario, identificador, bloquear=True)
    invitacion = get_object_or_404(
        InvitacionEmpleado.objects.select_for_update(), pk=invitacion_id, empresa=empresa,
        aceptada_en__isnull=True, cancelada_en__isnull=True,
    )
    invitacion.cancelada_en = timezone.now()
    invitacion.save(update_fields=["cancelada_en"])
    auditar(usuario, "revocar", "invitacion_empleado", invitacion.pk, empresa)
    return {"id": invitacion.pk, "estado": "cancelada"}


@transaction.atomic
def aceptar_invitacion(usuario: User, token: str) -> dict:
    digest = hashlib.sha256(token.encode()).hexdigest()
    invitacion = get_object_or_404(
        InvitacionEmpleado.objects.select_for_update().select_related("empresa").prefetch_related("sedes"),
        token_hash=digest,
    )
    if invitacion.aceptada_en or invitacion.cancelada_en or invitacion.vence_en <= timezone.now():
        raise ValidationError({"invitacion": "El enlace no es válido o ya venció."})
    perfil = PerfilUsuario.objects.filter(usuario=usuario).first()
    if not perfil or (perfil.correo or "").casefold() != invitacion.correo.casefold():
        raise PermissionDenied("La invitación pertenece a otro correo.")
    empresa = (
        empresa_con_cupo(invitacion.empresa_id, "empleado", usuario)
        if invitacion.rol in ROLES_CON_SEDE else invitacion.empresa
    )
    membresia = _asignar_usuario(
        empresa, usuario, invitacion.rol, list(invitacion.sedes.all())
    )
    invitacion.aceptada_en = timezone.now()
    invitacion.save(update_fields=["aceptada_en"])
    auditar(usuario, "aceptar", "invitacion_empleado", invitacion.pk, empresa)
    return _datos_membresia(membresia)
