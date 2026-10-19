from datetime import timedelta

from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.empresas.models import Empresa, RegistroAuditoria
from apps.empresas.repositories.empresas import empresas_propietario
from apps.empresas.services.auditoria import auditar
from apps.suscripciones.models import (
    ConfiguracionSuscripcion,
    EstadoSolicitud,
    EstadoSuscripcion,
    PagoSuscripcion,
    PeriodoSuscripcion,
    PlanSuscripcion,
    SolicitudSuscripcion,
    SuscripcionEmpresa,
    TipoSolicitud,
)
from apps.suscripciones.services.reglas import calcular_vencimiento


def _empresa_de(usuario: User, identificador: int, bloquear: bool = False) -> Empresa:
    consulta = empresas_propietario(usuario)
    if bloquear:
        consulta = consulta.select_for_update()
    return get_object_or_404(consulta, pk=identificador)


def serializar_plan(plan: PlanSuscripcion) -> dict:
    return {
        "id": plan.pk, "nombre": plan.nombre, "descripcion": plan.descripcion,
        "precio": str(plan.precio), "moneda": plan.moneda,
        "frecuencia": plan.frecuencia, "maximo_sedes": plan.maximo_sedes,
        "maximo_empleados": plan.maximo_empleados, "maximo_canchas": plan.maximo_canchas,
        "activo": plan.activo,
    }


def estado_efectivo(suscripcion: SuscripcionEmpresa) -> str:
    if (suscripcion.estado == EstadoSuscripcion.ACTIVA and suscripcion.fecha_vencimiento
            and suscripcion.fecha_vencimiento < timezone.localdate()
            and suscripcion.fecha_vencimiento + timedelta(days=dias_gracia()) < timezone.localdate()):
        return EstadoSuscripcion.VENCIDA
    return suscripcion.estado


def dias_gracia() -> int:
    return ConfiguracionSuscripcion.objects.filter(pk=1).values_list("dias_gracia", flat=True).first() or 0


def _resumen_actual(empresa: Empresa) -> dict | None:
    suscripcion = SuscripcionEmpresa.objects.filter(empresa=empresa).select_related("plan").first()
    if not suscripcion:
        return None
    periodos = suscripcion.periodos.select_related("plan").order_by("-fecha_inicio", "-id")
    return {
        "estado": estado_efectivo(suscripcion), "estado_registrado": suscripcion.estado,
        "plan": serializar_plan(suscripcion.plan),
        "fecha_inicio": suscripcion.fecha_inicio, "fecha_vencimiento": suscripcion.fecha_vencimiento,
        "importe_acordado": str(suscripcion.importe_acordado),
        "moneda_acordada": suscripcion.moneda_acordada,
        "frecuencia_acordada": suscripcion.frecuencia_acordada,
        "dias_gracia": dias_gracia(),
        "periodos": [{
            "fecha_inicio": p.fecha_inicio, "fecha_vencimiento": p.fecha_vencimiento,
            "plan": p.plan.nombre, "importe": str(p.importe_acordado), "moneda": p.moneda_acordada,
        } for p in periodos],
    }


def resumen_empresa(usuario: User, identificador: int) -> dict:
    empresa = _empresa_de(usuario, identificador)
    solicitudes = SolicitudSuscripcion.objects.filter(empresa=empresa).select_related("plan")
    return {
        "empresa_id": empresa.pk, "estado_empresa": empresa.estado,
        "suscripcion": _resumen_actual(empresa),
        "solicitudes": [{
            "id": s.pk, "plan": s.plan.nombre, "tipo": s.tipo, "estado": s.estado,
            "precio": str(s.precio_solicitado), "moneda": s.moneda_solicitada,
            "creada_en": s.creada_en,
        } for s in solicitudes.order_by("-creada_en")[:10]],
    }


def planes_disponibles(usuario: User) -> list[dict]:
    if not usuario.is_authenticated:
        raise PermissionDenied("Inicia sesión para consultar los planes.")
    return [serializar_plan(p) for p in PlanSuscripcion.objects.filter(activo=True)]


def planes_plataforma(usuario: User) -> list[dict]:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede consultar los planes.")
    return [serializar_plan(plan) for plan in PlanSuscripcion.objects.order_by("precio", "nombre")]


def modelo_plan_plataforma(usuario: User, identificador: int) -> PlanSuscripcion:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede gestionar planes.")
    return get_object_or_404(PlanSuscripcion, pk=identificador)


def consultar_dias_gracia(usuario: User) -> int:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede ver esta configuración.")
    return dias_gracia()


@transaction.atomic
def solicitar_suscripcion(usuario: User, identificador: int, datos: dict) -> dict:
    empresa = _empresa_de(usuario, identificador, bloquear=True)
    plan = get_object_or_404(PlanSuscripcion.objects.filter(activo=True), pk=datos["plan_id"])
    suscripcion = SuscripcionEmpresa.objects.filter(empresa=empresa).first()
    tipo = (
        TipoSolicitud.RENOVACION
        if suscripcion and suscripcion.estado != EstadoSuscripcion.CANCELADA
        else TipoSolicitud.ACTIVACION
    )
    if SolicitudSuscripcion.objects.filter(
        empresa=empresa, estado=EstadoSolicitud.PENDIENTE
    ).exists():
        raise ValidationError({"solicitud": "Ya existe una solicitud pendiente para esta empresa."})
    solicitud = SolicitudSuscripcion.objects.create(
        empresa=empresa, plan=plan, tipo=tipo, precio_solicitado=plan.precio,
        moneda_solicitada=plan.moneda, frecuencia_solicitada=plan.frecuencia,
        medio_declarado=datos.get("medio_declarado", ""),
        referencia_declarada=datos.get("referencia_declarada", ""),
        nota=datos.get("nota", ""), solicitada_por=usuario,
    )
    auditar(
        usuario, "solicitar", "suscripcion", solicitud.pk, empresa,
        {"tipo": tipo, "plan_id": plan.pk},
    )
    return {"id": solicitud.pk, "estado": solicitud.estado, "tipo": tipo}


def listar_solicitudes_plataforma(usuario: User, estado: str = "") -> list[dict]:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede revisar solicitudes.")
    solicitudes = SolicitudSuscripcion.objects.select_related(
        "empresa", "empresa__suscripcion", "plan", "solicitada_por", "revisada_por"
    )
    if estado in EstadoSolicitud.values:
        solicitudes = solicitudes.filter(estado=estado)
    RegistroAuditoria.objects.create(
        actor=usuario, accion="listar", recurso="solicitudes_suscripcion"
    )
    return [{
        "id": s.pk, "empresa_id": s.empresa_id, "empresa": s.empresa.nombre_visible,
        "estado_empresa": s.empresa.estado, "plan": serializar_plan(s.plan),
        "tipo": s.tipo, "estado": s.estado, "precio": str(s.precio_solicitado),
        "moneda": s.moneda_solicitada, "frecuencia": s.frecuencia_solicitada,
        "medio_declarado": s.medio_declarado, "referencia_declarada": s.referencia_declarada,
        "nota": s.nota, "solicitante": s.solicitada_por.get_full_name(),
        "suscripcion_actual": ({
            "estado": estado_efectivo(s.empresa.suscripcion),
            "vencimiento": s.empresa.suscripcion.fecha_vencimiento,
        } if hasattr(s.empresa, "suscripcion") else None),
        "creada_en": s.creada_en,
    } for s in solicitudes.order_by("creada_en", "id")]


@transaction.atomic
def resolver_solicitud(
    usuario: User, identificador: int, datos: dict
) -> dict:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede resolver solicitudes.")
    solicitud = get_object_or_404(
        SolicitudSuscripcion.objects.select_for_update().select_related("plan", "empresa"),
        pk=identificador,
    )
    if solicitud.estado != EstadoSolicitud.PENDIENTE:
        raise ValidationError({"solicitud": "Esta solicitud ya fue revisada."})
    aprobada = datos["aprobar"]
    solicitud.revisada_por = usuario
    solicitud.revisada_en = timezone.now()
    if not aprobada:
        solicitud.estado = EstadoSolicitud.RECHAZADA
        solicitud.save(update_fields=["estado", "revisada_por", "revisada_en"])
        auditar(usuario, "rechazar", "solicitud_suscripcion", solicitud.pk, solicitud.empresa)
        return {"id": solicitud.pk, "estado": solicitud.estado}
    importe = datos["importe_verificado"]
    if importe != solicitud.precio_solicitado:
        raise ValidationError({"importe_verificado": "El importe debe coincidir con el precio solicitado."})
    Empresa.objects.select_for_update().get(pk=solicitud.empresa_id)
    inicio = datos.get("fecha_inicio") or timezone.localdate()
    hoy = timezone.localdate()
    suscripcion = SuscripcionEmpresa.objects.filter(empresa=solicitud.empresa).first()
    if inicio < hoy:
        raise ValidationError({"fecha_inicio": "La vigencia no puede comenzar en una fecha pasada."})
    if (suscripcion and suscripcion.estado != EstadoSuscripcion.CANCELADA
            and suscripcion.fecha_vencimiento and inicio <= suscripcion.fecha_vencimiento):
        raise ValidationError({
            "fecha_inicio": "La renovación debe comenzar después del periodo ya contratado."
        })
    vencimiento = calcular_vencimiento(inicio, solicitud.frecuencia_solicitada)
    if suscripcion is None:
        suscripcion = SuscripcionEmpresa.objects.create(
            empresa=solicitud.empresa, plan=solicitud.plan, estado=EstadoSuscripcion.ACTIVA,
            fecha_inicio=inicio, fecha_vencimiento=vencimiento,
            importe_acordado=solicitud.precio_solicitado,
            moneda_acordada=solicitud.moneda_solicitada,
            frecuencia_acordada=solicitud.frecuencia_solicitada,
        )
    else:
        suscripcion.plan = solicitud.plan
        suscripcion.estado = EstadoSuscripcion.ACTIVA
        suscripcion.fecha_inicio = inicio
        suscripcion.fecha_vencimiento = vencimiento
        suscripcion.importe_acordado = solicitud.precio_solicitado
        suscripcion.moneda_acordada = solicitud.moneda_solicitada
        suscripcion.frecuencia_acordada = solicitud.frecuencia_solicitada
        suscripcion.save()
    periodo = PeriodoSuscripcion.objects.create(
        suscripcion=suscripcion, plan=solicitud.plan, fecha_inicio=inicio,
        fecha_vencimiento=vencimiento, importe_acordado=solicitud.precio_solicitado,
        moneda_acordada=solicitud.moneda_solicitada,
        frecuencia_acordada=solicitud.frecuencia_solicitada, creado_por=usuario,
    )
    if importe > 0:
        PagoSuscripcion.objects.create(
            solicitud=solicitud, importe_verificado=importe, moneda=solicitud.moneda_solicitada,
            referencia=datos.get("referencia_verificada", solicitud.referencia_declarada),
            medio=datos.get("medio_verificado", solicitud.medio_declarado), confirmado_por=usuario,
        )
    solicitud.estado = EstadoSolicitud.APROBADA
    solicitud.save(update_fields=["estado", "revisada_por", "revisada_en"])
    auditar(
        usuario, "activar_suscripcion", "periodo_suscripcion", periodo.pk,
        solicitud.empresa,
        {"solicitud_id": solicitud.pk, "importe": str(importe),
         "fecha_inicio": inicio.isoformat(), "fecha_vencimiento": vencimiento.isoformat()},
    )
    return {"id": solicitud.pk, "estado": solicitud.estado, "vencimiento": vencimiento}


@transaction.atomic
def cambiar_estado(usuario: User, empresa_id: int, nuevo_estado: str) -> dict:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede cambiar suscripciones.")
    suscripcion = get_object_or_404(
        SuscripcionEmpresa.objects.select_for_update().select_related("empresa"),
        empresa_id=empresa_id,
    )
    transiciones = {
        EstadoSuscripcion.ACTIVA: {EstadoSuscripcion.SUSPENDIDA, EstadoSuscripcion.CANCELADA},
        EstadoSuscripcion.VENCIDA: {EstadoSuscripcion.SUSPENDIDA, EstadoSuscripcion.CANCELADA},
        EstadoSuscripcion.SUSPENDIDA: {EstadoSuscripcion.CANCELADA},
        EstadoSuscripcion.CANCELADA: set(),
    }
    actual = estado_efectivo(suscripcion)
    if nuevo_estado not in transiciones.get(actual, set()):
        raise ValidationError({"estado": "La suscripción no puede pasar a ese estado."})
    anterior = actual
    suscripcion.estado = nuevo_estado
    suscripcion.save(update_fields=["estado", "actualizado_en"])
    auditar(
        usuario, "cambiar_estado", "suscripcion", suscripcion.pk, suscripcion.empresa,
        {"anterior": anterior, "nuevo": nuevo_estado},
    )
    return {"empresa_id": empresa_id, "estado": nuevo_estado}


@transaction.atomic
def configurar_dias_gracia(usuario: User, dias: int) -> dict:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede cambiar esta configuración.")
    configuracion, _ = ConfiguracionSuscripcion.objects.update_or_create(
        pk=1, defaults={"dias_gracia": dias, "actualizado_por": usuario}
    )
    auditar(
        usuario, "configurar_vigencia", "configuracion_suscripcion",
        configuracion.pk, datos={"dias_gracia": dias},
    )
    return {"dias_gracia": configuracion.dias_gracia}


@transaction.atomic
def guardar_plan(usuario: User, identificador: int | None, datos: dict) -> dict:
    if not usuario.is_superuser:
        raise PermissionDenied("Solo el superadministrador puede gestionar planes.")
    plan = (
        get_object_or_404(PlanSuscripcion.objects.select_for_update(), pk=identificador)
        if identificador else PlanSuscripcion()
    )
    campos = (
        "nombre", "descripcion", "precio", "moneda", "frecuencia",
        "maximo_sedes", "maximo_empleados", "maximo_canchas", "activo",
    )
    cambios = {campo: datos[campo] for campo in campos if campo in datos}
    for campo, valor in cambios.items():
        setattr(plan, campo, valor)
    try:
        with transaction.atomic():
            plan.save()
    except IntegrityError:
        raise ValidationError({"nombre": "Ya existe un plan con ese nombre."}) from None
    auditar(
        usuario, "crear" if identificador is None else "actualizar",
        "plan_suscripcion", plan.pk, datos={"campos": sorted(cambios)},
    )
    return serializar_plan(plan)
