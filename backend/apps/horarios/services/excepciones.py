from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.repositories.alcance import sede_administrable, sedes_visibles
from apps.empresas.services.auditoria import auditar
from apps.horarios.models import (
    ExcepcionHorario,
    HorarioSede,
    TipoExcepcionHorario,
)
from apps.horarios.repositories.excepciones import excepciones_visibles
from apps.horarios.services.horarios import _datos_intervalo
from apps.reservas.services.eventos import programar_cambio_sede_intervalo
from apps.sedes.models import Sede
from apps.sedes.services.sedes import _exigir_suscripcion

ZONA = ZoneInfo(settings.TIME_ZONE)


def datos_excepcion(excepcion: ExcepcionHorario) -> dict:
    creador = excepcion.creado_por
    return {
        "id": excepcion.pk,
        "sede_id": excepcion.sede_id,
        "cancha_id": excepcion.cancha_id,
        "tipo": excepcion.tipo,
        "fecha_inicio": timezone.localtime(excepcion.fecha_inicio, ZONA).isoformat(),
        "fecha_fin": timezone.localtime(excepcion.fecha_fin, ZONA).isoformat(),
        "motivo": excepcion.motivo,
        "creado_por_id": excepcion.creado_por_id,
        "creado_por": creador.get_full_name() or creador.get_username(),
        "creada_en": timezone.localtime(excepcion.creada_en, ZONA).isoformat(),
        "anulada": excepcion.anulada,
        "anulada_por_id": excepcion.anulada_por_id,
        "anulada_en": (
            timezone.localtime(excepcion.anulada_en, ZONA).isoformat()
            if excepcion.anulada_en else None
        ),
    }


def listar_excepciones(usuario: User, filtros: dict) -> list[dict]:
    desde = filtros.get("desde")
    hasta = filtros.get("hasta")
    if desde and hasta and hasta < desde:
        raise ValidationError({"hasta": "La fecha final debe ser igual o posterior a la inicial."})
    inicio = timezone.make_aware(datetime.combine(desde, time.min), ZONA) if desde else None
    fin = timezone.make_aware(datetime.combine(hasta + timedelta(days=1), time.min), ZONA) if hasta else None
    consulta = excepciones_visibles(
        usuario, filtros.get("sede"), filtros.get("cancha")
    )
    if desde:
        consulta = consulta.filter(fecha_fin__gt=inicio)
    if fin:
        consulta = consulta.filter(fecha_inicio__lt=fin)
    if usuario.is_superuser:
        from apps.empresas.models import AccesoPlataforma

        AccesoPlataforma.objects.create(usuario=usuario, accion="listar_excepciones_horario")
    return [datos_excepcion(item) for item in consulta]


def _fecha_hora_local(fecha: date, hora: time, dia_extra: int = 0) -> datetime:
    if isinstance(hora, str):
        hora = time.fromisoformat(hora)
    return timezone.make_aware(
        datetime.combine(fecha + timedelta(days=dia_extra), hora.replace(tzinfo=None)),
        ZONA,
    )


def _cubierto_por_horario_efectivo_sede(sede_id: int, inicio: datetime, fin: datetime) -> bool:
    try:
        horario = HorarioSede.objects.get(sede_id=sede_id, configurado=True)
    except HorarioSede.DoesNotExist:
        return False
    intervalos = [_datos_intervalo(item) for item in horario.intervalos.all()]
    if not intervalos:
        return False

    consulta = ExcepcionHorario.objects.filter(
        sede_id=sede_id, cancha__isnull=True, anulada=False,
        fecha_inicio__lt=fin, fecha_fin__gt=inicio,
    )
    if consulta.filter(tipo=TipoExcepcionHorario.CIERRE).exists():
        return False
    segmentos = [
        (item.fecha_inicio, item.fecha_fin)
        for item in consulta.filter(tipo=TipoExcepcionHorario.AMPLIACION)
    ]

    inicio_local = timezone.localtime(inicio, ZONA).date() - timedelta(days=1)
    fin_local = timezone.localtime(fin, ZONA).date()
    cursor_fecha = inicio_local
    while cursor_fecha <= fin_local:
        for intervalo in intervalos:
            if intervalo["dia_semana"] != cursor_fecha.weekday():
                continue
            hora_apertura = intervalo["hora_apertura"]
            hora_cierre = intervalo["hora_cierre"]
            dia_cierre = 1 if hora_cierre <= hora_apertura else 0
            apertura = _fecha_hora_local(cursor_fecha, hora_apertura)
            cierre = _fecha_hora_local(cursor_fecha, hora_cierre, dia_cierre)
            if apertura < fin and cierre > inicio:
                segmentos.append((apertura, cierre))

        cursor_fecha += timedelta(days=1)

    segmentos.sort(key=lambda periodo: periodo[0])
    cubierto_hasta = inicio
    for apertura, cierre in segmentos:
        if apertura > cubierto_hasta:
            break
        if cierre > cubierto_hasta:
            cubierto_hasta = cierre
        if cubierto_hasta >= fin:
            return True
    return False


def _validar_solape(excepcion: ExcepcionHorario) -> None:
    consulta = ExcepcionHorario.objects.filter(
        sede=excepcion.sede,
        tipo=excepcion.tipo,
        anulada=False,
        fecha_inicio__lt=excepcion.fecha_fin,
        fecha_fin__gt=excepcion.fecha_inicio,
    )
    consulta = consulta.filter(cancha=excepcion.cancha) if excepcion.cancha_id else consulta.filter(cancha__isnull=True)
    if consulta.exists():
        raise ValidationError({
            "fecha_inicio": "Ya existe una excepción activa del mismo tipo y alcance que se superpone."
        })


@transaction.atomic
def crear_excepcion(usuario: User, datos: dict) -> dict:
    sede_visible = get_object_or_404(sedes_visibles(usuario), pk=datos["sede_id"])
    sede = get_object_or_404(
        Sede.objects.select_for_update().select_related("empresa"), pk=sede_visible.pk
    )
    if not sede_administrable(usuario, sede.pk):
        raise PermissionDenied("No tienes acceso para gestionar excepciones en esta sede.")
    if not usuario.is_superuser:
        _exigir_suscripcion(sede.empresa)

    cancha = None
    if datos.get("cancha_id") is not None:
        cancha = get_object_or_404(
            canchas_visibles(usuario).select_for_update(),
            pk=datos["cancha_id"], sede=sede,
        )
    excepcion = ExcepcionHorario(
        sede=sede,
        cancha=cancha,
        tipo=datos["tipo"],
        fecha_inicio=datos["fecha_inicio"],
        fecha_fin=datos["fecha_fin"],
        motivo=datos["motivo"],
        creado_por=usuario,
    )
    _validar_solape(excepcion)
    if excepcion.tipo == TipoExcepcionHorario.AMPLIACION and cancha:
        if not _cubierto_por_horario_efectivo_sede(
            sede.pk, excepcion.fecha_inicio, excepcion.fecha_fin
        ):
            raise ValidationError({
                "fecha_inicio": "La ampliación de cancha debe quedar dentro del horario efectivo de sede."
            })
    excepcion.save()
    auditar(usuario, "crear", "excepcion_horario", excepcion.pk, sede.empresa, {
        "sede_id": sede.pk, "cancha_id": cancha.pk if cancha else None,
        "tipo": excepcion.tipo, "motivo": excepcion.motivo,
    })
    programar_cambio_sede_intervalo(
        sede.pk, excepcion.fecha_inicio, excepcion.fecha_fin,
        "excepcion_actualizada", cancha.pk if cancha else None,
    )
    return datos_excepcion(excepcion)


@transaction.atomic
def anular_excepcion(usuario: User, excepcion_id: int) -> dict:
    excepcion = get_object_or_404(
        excepciones_visibles(usuario).select_for_update(of=("self",)), pk=excepcion_id
    )
    if not sede_administrable(usuario, excepcion.sede_id):
        raise PermissionDenied("No tienes acceso para anular esta excepción.")
    sede = get_object_or_404(
        Sede.objects.select_for_update().select_related("empresa"), pk=excepcion.sede_id
    )
    if excepcion.anulada:
        raise ValidationError({"anulada": "La excepción ya fue anulada."})
    excepcion.anulada = True
    excepcion.anulada_por = usuario
    excepcion.anulada_en = timezone.now()
    excepcion.save(update_fields=["anulada", "anulada_por", "anulada_en"])
    auditar(usuario, "anular", "excepcion_horario", excepcion.pk, sede.empresa, {
        "sede_id": excepcion.sede_id, "cancha_id": excepcion.cancha_id,
        "tipo": excepcion.tipo,
    })
    programar_cambio_sede_intervalo(
        sede.pk, excepcion.fecha_inicio, excepcion.fecha_fin,
        "excepcion_actualizada", excepcion.cancha_id,
    )
    return datos_excepcion(excepcion)
