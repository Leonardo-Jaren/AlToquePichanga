from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone

from apps.canchas.models import Cancha, EstadoCancha
from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.models import RegistroAuditoria
from apps.horarios.models import (
    ExcepcionHorario,
    HorarioCancha,
    HorarioSede,
    TipoExcepcionHorario,
)
from apps.horarios.services.horarios import _datos_intervalo, _dias_heredados
from apps.sedes.models import Sede

ZONA = ZoneInfo(settings.TIME_ZONE)
DURACION_BLOQUE = timedelta(hours=1)


def _localizar(fecha: date, hora: time, extra: int = 0) -> datetime:
    if isinstance(hora, str):
        hora = time.fromisoformat(hora)
    return timezone.make_aware(
        datetime.combine(fecha + timedelta(days=extra), hora.replace(tzinfo=None)), ZONA
    )


def _periodo_semanal(fecha: date, intervalo: dict) -> tuple[datetime, datetime]:
    apertura = intervalo["hora_apertura"]
    cierre = intervalo["hora_cierre"]
    dia_extra = 1 if cierre <= apertura else 0
    return _localizar(fecha, apertura), _localizar(fecha, cierre, dia_extra)


def _unir_periodos(periodos: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime]]:
    unidos: list[list[datetime]] = []
    for inicio, fin in sorted(periodos, key=lambda periodo: periodo[0]):
        if fin <= inicio:
            continue
        if unidos and inicio <= unidos[-1][1]:
            unidos[-1][1] = max(unidos[-1][1], fin)
        else:
            unidos.append([inicio, fin])
    return [(periodo[0], periodo[1]) for periodo in unidos]


def _horarios(cancha: Cancha) -> tuple[list[dict], list[dict]]:
    try:
        horario_sede = HorarioSede.objects.get(sede_id=cancha.sede_id, configurado=True)
        intervalos_sede = [_datos_intervalo(item) for item in horario_sede.intervalos.all()]
    except HorarioSede.DoesNotExist:
        intervalos_sede = []
    try:
        horario_cancha = HorarioCancha.objects.get(cancha=cancha, configurado=True)
    except HorarioCancha.DoesNotExist:
        horario_cancha = None
    intervalos_propios = (
        [_datos_intervalo(item) for item in horario_cancha.intervalos.all()]
        if horario_cancha else []
    )
    heredados = set(_dias_heredados(horario_cancha))
    return [item for item in intervalos_sede if item["dia_semana"] in heredados], [
        item for item in intervalos_propios if item["dia_semana"] not in heredados
    ]


def _excepciones(
    sede_id: int, cancha_id: int, inicio: datetime, fin: datetime
) -> list[ExcepcionHorario]:
    return list(ExcepcionHorario.objects.filter(
        anulada=False,
        sede_id=sede_id,
        fecha_inicio__lt=fin,
        fecha_fin__gt=inicio,
    ).filter(
        # Los cierres de sede aplican a todas las canchas; sus ampliaciones también
        # extienden el horario efectivo de sede.
        Q(cancha__isnull=True) | Q(cancha_id=cancha_id),
    ).order_by("fecha_inicio", "id"))



def _estado_bloque(
    cancha: Cancha,
    sede: Sede,
    inicio: datetime,
    excepciones: list[ExcepcionHorario],
    ahora: datetime,
) -> tuple[str, bool, str | None]:
    if inicio < ahora:
        return "pasada", False, "El bloque ya comenzó."
    if not sede.activa:
        return "sede_inactiva", False, "La sede está inactiva."
    if cancha.estado == EstadoCancha.INACTIVA:
        return "cancha_inactiva", False, "La cancha está inactiva."
    if cancha.estado == EstadoCancha.MANTENIMIENTO:
        return "mantenimiento", False, "La cancha está en mantenimiento."
    cierres = [
        item for item in excepciones
        if item.tipo == TipoExcepcionHorario.CIERRE
        and item.fecha_inicio < inicio + DURACION_BLOQUE
        and item.fecha_fin > inicio
    ]
    if cierres:
        return "cerrada", False, f"Cierre: {cierres[0].motivo}"
    return "operativa", True, None


def consultar_disponibilidad_operativa(
    usuario: User, cancha_id: int, desde: date, hasta: date
) -> dict:
    cancha = get_object_or_404(
        canchas_visibles(usuario).select_related("sede", "sede__empresa"), pk=cancha_id
    )
    sede = cancha.sede
    inicio_rango = _localizar(desde, time.min)
    fin_rango = _localizar(hasta + timedelta(days=1), time.min)
    escaneo_inicio = inicio_rango - timedelta(days=1)
    excepciones = _excepciones(sede.pk, cancha.pk, escaneo_inicio, fin_rango)
    intervalos_sede, intervalos_propios = _horarios(cancha)
    periodos: list[tuple[datetime, datetime]] = []

    cursor_fecha = desde - timedelta(days=1)
    while cursor_fecha <= hasta:
        intervalos_dia = [
            item for item in intervalos_sede
            if item["dia_semana"] == cursor_fecha.weekday()
        ]
        intervalos_dia.extend(
            item for item in intervalos_propios
            if item["dia_semana"] == cursor_fecha.weekday()
        )
        periodos.extend(_periodo_semanal(cursor_fecha, item) for item in intervalos_dia)
        cursor_fecha += timedelta(days=1)

    periodos.extend(
        (item.fecha_inicio, item.fecha_fin)
        for item in excepciones
        if item.tipo == TipoExcepcionHorario.AMPLIACION
    )
    periodos = _unir_periodos([
        (max(inicio_rango - timedelta(days=1), inicio), min(fin_rango, fin))
        for inicio, fin in periodos
        if inicio < fin_rango and fin > inicio_rango - timedelta(days=1)
    ])

    ahora = timezone.localtime(timezone.now(), ZONA)
    bloques: list[dict] = []
    for apertura, cierre in periodos:
        cursor = apertura
        while cursor + DURACION_BLOQUE <= cierre:
            final = cursor + DURACION_BLOQUE
            if inicio_rango <= cursor < fin_rango:
                estado, habilitada, motivo = _estado_bloque(
                    cancha, sede, cursor, excepciones, ahora
                )
                bloques.append({
                    "fecha_inicio": cursor.isoformat(),
                    "fecha_fin": final.isoformat(),
                    "estado": estado,
                    "habilitada_operativamente": habilitada,
                    "motivo": motivo,
                    "considera_reservas": False,
                })
            cursor = final

    resultado = {
        "cancha_id": cancha.pk,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "zona_horaria": settings.TIME_ZONE,
        "considera_reservas": False,
        "bloques": bloques,
    }
    if usuario.is_superuser:
        RegistroAuditoria.objects.create(
            actor=usuario, empresa=sede.empresa,
            accion="consultar_disponibilidad_operativa",
            recurso="disponibilidad_operativa", recurso_id=cancha.pk,
            datos={"desde": desde.isoformat(), "hasta": hasta.isoformat()},
        )
    return resultado
