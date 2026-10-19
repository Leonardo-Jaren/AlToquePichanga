"""Horarios y excepciones del fixture local, asociados a sedes/canchas marcadas."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.utils import timezone

from apps.canchas.models import Cancha
from apps.horarios.models import (
    ExcepcionHorario,
    HorarioCancha,
    HorarioSede,
    IntervaloHorarioCancha,
    IntervaloHorarioSede,
    TipoExcepcionHorario,
)
from apps.sedes.models import Sede
from apps.usuarios.services.datos_demo import MARCA, identidad_demo


def _intervalos_semana(horario, modelo_intervalo, intervalos: list[tuple[int, time, time]]) -> None:
    actuales = list(modelo_intervalo.objects.filter(horario=horario).order_by(
        "dia_semana", "hora_apertura", "id"
    ).values_list("dia_semana", "hora_apertura", "hora_cierre"))
    esperados = sorted(intervalos)
    if actuales != esperados:
        modelo_intervalo.objects.filter(horario=horario).delete()
        modelo_intervalo.objects.bulk_create([
            modelo_intervalo(
                horario=horario, dia_semana=dia,
                hora_apertura=apertura, hora_cierre=cierre,
            )
            for dia, apertura, cierre in esperados
        ])


def _horarios(sedes: dict, canchas: dict) -> None:
    intervalos_sede = [
        (dia, time(15, 0), time(23, 0)) if dia < 5
        else (dia, time(9, 0), time(23, 0))
        for dia in range(7)
    ]
    for sede in sedes.values():
        horario, _ = HorarioSede.objects.get_or_create(
            sede=sede, defaults={"configurado": True}
        )
        if not horario.configurado:
            horario.configurado = True
            horario.save(update_fields=["configurado", "actualizado_en"])
        _intervalos_semana(horario, IntervaloHorarioSede, intervalos_sede)

    intervalos_cancha_propia = [
        (dia, time(16, 0), time(22, 0)) for dia in range(5)
    ]
    for clave, cancha in canchas.items():
        propia = clave == "cancha_a_propia"
        horario, _ = HorarioCancha.objects.get_or_create(
            cancha=cancha,
            defaults={
                "hereda_horario_sede": not propia,
                "dias_heredados": [5, 6] if propia else [],
                "configurado": propia,
            },
        )
        horario.hereda_horario_sede = not propia
        horario.dias_heredados = [5, 6] if propia else []
        horario.configurado = propia
        horario.save(update_fields=[
            "hereda_horario_sede", "dias_heredados", "configurado", "actualizado_en",
        ])
        _intervalos_semana(
            horario,
            IntervaloHorarioCancha,
            intervalos_cancha_propia if propia else [],
        )


def _proxima_fecha(dia_semana: int) -> date:
    hoy = timezone.localdate()
    diferencia = (dia_semana - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=diferencia)


def _fecha_hora(dia: date, hora: time) -> datetime:
    return timezone.make_aware(datetime.combine(dia, hora), timezone.get_current_timezone())


def _excepcion(
    *, sede: Sede, cancha: Cancha | None, tipo: str, clave: str,
    inicio: datetime, fin: datetime, motivo: str, creador: User,
) -> None:
    marca = f"{MARCA} {identidad_demo(clave)}: {motivo}"
    prefijo_marca = f"{MARCA} {identidad_demo(clave)}:"
    coincidencias = list(ExcepcionHorario.objects.filter(motivo__startswith=prefijo_marca)[:2])
    if len(coincidencias) > 1:
        raise CommandError(f"Hay excepciones demo duplicadas: {clave}.")
    excepcion = coincidencias[0] if coincidencias else None
    colision = ExcepcionHorario.objects.filter(
        sede=sede, cancha=cancha, tipo=tipo,
        anulada=False, fecha_inicio__lt=fin, fecha_fin__gt=inicio,
    )
    if excepcion:
        colision = colision.exclude(pk=excepcion.pk)
    if colision.exists():
        raise CommandError(f"Hay una excepción no demo con el horario reservado para {clave}.")
    if excepcion is None:
        ExcepcionHorario.objects.create(
            sede=sede, cancha=cancha, tipo=tipo,
            fecha_inicio=inicio, fecha_fin=fin, motivo=marca, creado_por=creador,
        )
        return
    excepcion.sede = sede
    excepcion.cancha = cancha
    excepcion.tipo = tipo
    excepcion.fecha_inicio = inicio
    excepcion.fecha_fin = fin
    excepcion.motivo = marca
    excepcion.creado_por = creador
    excepcion.anulada = False
    excepcion.anulada_por = None
    excepcion.anulada_en = None
    excepcion.save()


def crear_horarios_demo(sedes: dict, canchas: dict, usuarios: dict) -> None:
    _horarios(sedes, canchas)
    proximo_sabado = _proxima_fecha(5)
    _excepcion(
        sede=sedes["sede_a_centro"], cancha=None,
        tipo=TipoExcepcionHorario.AMPLIACION,
        clave="ampliacion-a-centro",
        inicio=_fecha_hora(proximo_sabado, time(7, 0)),
        fin=_fecha_hora(proximo_sabado, time(9, 0)),
        motivo="Ampliación especial de horario",
        creador=usuarios["superadmin"],
    )
    proximo_viernes = _proxima_fecha(4)
    _excepcion(
        sede=sedes["sede_a_centro"], cancha=canchas["cancha_a_propia"],
        tipo=TipoExcepcionHorario.CIERRE,
        clave="mantenimiento-a-propia",
        inicio=_fecha_hora(proximo_viernes, time(18, 0)),
        fin=_fecha_hora(proximo_viernes, time(20, 0)),
        motivo="Cierre por mantenimiento programado",
        creador=usuarios["superadmin"],
    )
