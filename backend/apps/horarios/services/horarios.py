from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.canchas.models import Cancha
from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.models import RegistroAuditoria
from apps.empresas.repositories.alcance import sede_administrable, sedes_visibles
from apps.empresas.services.auditoria import auditar
from apps.horarios.models import (
    HorarioCancha,
    HorarioSede,
    IntervaloHorarioCancha,
    IntervaloHorarioSede,
)
from apps.horarios.services.reglas_semanales import (
    intervalos_contenidos,
    validar_intervalos,
)
from apps.sedes.models import Sede
from apps.sedes.services.sedes import _exigir_suscripcion


def _datos_intervalo(intervalo) -> dict:
    return {
        "dia_semana": intervalo.dia_semana,
        "hora_apertura": intervalo.hora_apertura.strftime("%H:%M"),
        "hora_cierre": intervalo.hora_cierre.strftime("%H:%M"),
    }


def _intervalos_sede(sede_id: int) -> list[dict]:
    try:
        horario = HorarioSede.objects.get(sede_id=sede_id, configurado=True)
    except HorarioSede.DoesNotExist:
        return []
    return [_datos_intervalo(item) for item in horario.intervalos.all()]


def _intervalos_cancha(cancha_id: int) -> list[dict]:
    try:
        horario = HorarioCancha.objects.get(cancha_id=cancha_id, configurado=True)
    except HorarioCancha.DoesNotExist:
        return []
    return [_datos_intervalo(item) for item in horario.intervalos.all()]


def _dias_heredados(horario: HorarioCancha | None) -> list[int]:
    if horario is None or not horario.configurado or horario.hereda_horario_sede:
        return list(range(7))
    return list(horario.dias_heredados)


def _intervalos_efectivos_cancha(cancha: Cancha, horario: HorarioCancha | None) -> list[dict]:
    heredados = set(_dias_heredados(horario))
    propios = (
        _intervalos_cancha(cancha.pk)
        if horario and horario.configurado and not horario.hereda_horario_sede else []
    )
    intervalos_sede = _intervalos_sede(cancha.sede_id)
    efectivos = [item for item in intervalos_sede if item["dia_semana"] in heredados]
    efectivos.extend(item for item in propios if item["dia_semana"] not in heredados)
    return sorted(efectivos, key=lambda item: (item["dia_semana"], item["hora_apertura"]))


def _horario_sede_visible(usuario: User, sede_id: int) -> Sede:
    return get_object_or_404(sedes_visibles(usuario).select_related("empresa"), pk=sede_id)


def _horario_cancha_visible(usuario: User, cancha_id: int) -> Cancha:
    return get_object_or_404(canchas_visibles(usuario), pk=cancha_id)


def _dto_horario_sede(sede: Sede, horario: HorarioSede | None) -> dict:
    return {
        "sede_id": sede.pk,
        "configurado": bool(horario and horario.configurado),
        "zona_horaria": "America/Lima",
        "intervalos": [
            _datos_intervalo(item) for item in horario.intervalos.all()
        ] if horario and horario.configurado else [],
    }


def consultar_horario_sede(usuario: User, sede_id: int) -> dict:
    sede = _horario_sede_visible(usuario, sede_id)
    try:
        horario = HorarioSede.objects.get(sede=sede)
    except HorarioSede.DoesNotExist:
        horario = None
    if usuario.is_superuser:
        RegistroAuditoria.objects.create(
            actor=usuario, empresa=sede.empresa, accion="consultar_horario",
            recurso="horario_sede", recurso_id=horario.pk if horario else sede.pk,
        )
    return _dto_horario_sede(sede, horario)


@transaction.atomic
def guardar_horario_sede(usuario: User, sede_id: int, intervalos: list[dict]) -> dict:
    sede_visible = _horario_sede_visible(usuario, sede_id)
    sede = get_object_or_404(
        Sede.objects.select_for_update().select_related("empresa"),
        pk=sede_visible.pk,
    )
    if not sede_administrable(usuario, sede.pk):
        raise PermissionDenied("No tienes acceso para modificar el horario de esta sede.")
    if not usuario.is_superuser:
        _exigir_suscripcion(sede.empresa)
    normalizados = validar_intervalos(intervalos)

    canchas = list(Cancha.objects.select_for_update().filter(sede=sede).order_by("id"))
    horarios_propios = HorarioCancha.objects.filter(
        cancha__in=canchas, configurado=True
    ).prefetch_related("intervalos")
    for horario_cancha in horarios_propios:
        heredados = set(_dias_heredados(horario_cancha))
        actuales = [
            _datos_intervalo(item) for item in horario_cancha.intervalos.all()
            if item.dia_semana not in heredados
        ]
        if not intervalos_contenidos(actuales, normalizados):
            raise ValidationError({
                "intervalos": (
                    "El nuevo horario de sede dejaría fuera el horario propio de una cancha. "
                    "Ajusta primero el horario de esa cancha."
                )
            })

    horario, _ = HorarioSede.objects.get_or_create(sede=sede)
    horario.configurado = True
    horario.save(update_fields=["configurado", "actualizado_en"])
    horario.intervalos.all().delete()
    IntervaloHorarioSede.objects.bulk_create([
        IntervaloHorarioSede(horario=horario, **item) for item in normalizados
    ])
    auditar(usuario, "actualizar", "horario_sede", horario.pk, sede.empresa, {
        "sede_id": sede.pk, "intervalos": len(normalizados),
    })
    return _dto_horario_sede(sede, horario)


def consultar_horario_cancha(usuario: User, cancha_id: int) -> dict:
    cancha = _horario_cancha_visible(usuario, cancha_id)
    try:
        horario = HorarioCancha.objects.get(cancha=cancha)
    except HorarioCancha.DoesNotExist:
        horario = None
    hereda = horario.hereda_horario_sede if horario else True
    heredados = _dias_heredados(horario)
    propios = (
        [_datos_intervalo(item) for item in horario.intervalos.all()]
        if horario and horario.configurado and not hereda else []
    )
    propios = [item for item in propios if item["dia_semana"] not in heredados]
    efectivos = _intervalos_efectivos_cancha(cancha, horario)
    if usuario.is_superuser:
        RegistroAuditoria.objects.create(
            actor=usuario, empresa=cancha.sede.empresa, accion="consultar_horario",
            recurso="horario_cancha", recurso_id=horario.pk if horario else cancha.pk,
        )
    return _dto_horario_cancha(cancha, horario, hereda, heredados, propios, efectivos)


def _dto_horario_cancha(
    cancha: Cancha,
    horario: HorarioCancha | None,
    hereda: bool,
    heredados: list[int],
    propios: list[dict],
    efectivos: list[dict],
) -> dict:
    return {
        "cancha_id": cancha.pk,
        "sede_id": cancha.sede_id,
        "configurado": bool(horario and horario.configurado),
        "hereda_horario_sede": hereda,
        "dias_heredados": [] if hereda else heredados,
        "intervalos": propios,
        "intervalos_efectivos": efectivos,
        "zona_horaria": "America/Lima",
    }


@transaction.atomic
def guardar_horario_cancha(
    usuario: User, cancha_id: int, hereda: bool, dias_heredados: list[int],
    intervalos: list[dict]
) -> dict:
    cancha_visible = _horario_cancha_visible(usuario, cancha_id)
    sede = get_object_or_404(
        Sede.objects.select_for_update().select_related("empresa"),
        pk=cancha_visible.sede_id,
    )
    if not sede_administrable(usuario, sede.pk):
        raise PermissionDenied("No tienes acceso para modificar el horario de esta cancha.")
    if not usuario.is_superuser:
        _exigir_suscripcion(sede.empresa)
    cancha = get_object_or_404(
        canchas_visibles(usuario).select_for_update(), pk=cancha_id, sede=sede
    )

    normalizados = validar_intervalos(intervalos)
    heredados = sorted(set(dias_heredados))
    if hereda and (normalizados or heredados):
        raise ValidationError({
            "hereda_horario_sede": "Con herencia completa, deja vacíos los días heredados y los intervalos propios."
        })
    if not hereda:
        if any(dia < 0 or dia > 6 for dia in heredados):
            raise ValidationError({"dias_heredados": "Usa días de semana entre 0 y 6."})
        if len(heredados) != len(dias_heredados):
            raise ValidationError({"dias_heredados": "No repitas días heredados."})
        if any(item["dia_semana"] in heredados for item in normalizados):
            raise ValidationError({
                "intervalos": "No agregues intervalos propios a un día que hereda el horario de sede."
            })
        try:
            horario_sede = HorarioSede.objects.get(sede=sede, configurado=True)
        except HorarioSede.DoesNotExist as exc:
            raise ValidationError({
                "hereda_horario_sede": "Configura primero el horario semanal de la sede."
            }) from exc
        sede_intervalos = [_datos_intervalo(item) for item in horario_sede.intervalos.all()]
        if not intervalos_contenidos(normalizados, sede_intervalos):
            raise ValidationError({
                "intervalos": "El horario de la cancha debe quedar dentro del horario semanal de sede."
            })

    horario, _ = HorarioCancha.objects.get_or_create(cancha=cancha)
    horario.hereda_horario_sede = hereda
    horario.dias_heredados = [] if hereda else heredados
    horario.configurado = True
    horario.save(update_fields=[
        "hereda_horario_sede", "dias_heredados", "configurado", "actualizado_en"
    ])
    horario.intervalos.all().delete()
    if normalizados:
        IntervaloHorarioCancha.objects.bulk_create([
            IntervaloHorarioCancha(horario=horario, **item) for item in normalizados
        ])
    auditar(usuario, "actualizar", "horario_cancha", horario.pk, sede.empresa, {
        "cancha_id": cancha.pk, "hereda_horario_sede": hereda,
        "dias_heredados": [] if hereda else heredados,
        "intervalos": len(normalizados),
    })
    horario.refresh_from_db()
    propios = [
        _datos_intervalo(item) for item in horario.intervalos.all()
        if item.dia_semana not in set(_dias_heredados(horario))
    ] if not horario.hereda_horario_sede else []
    heredados_final = _dias_heredados(horario)
    efectivos = _intervalos_efectivos_cancha(cancha, horario)
    return _dto_horario_cancha(
        cancha, horario, horario.hereda_horario_sede, heredados_final, propios, efectivos
    )
