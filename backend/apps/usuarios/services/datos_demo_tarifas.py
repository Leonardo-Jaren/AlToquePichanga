"""Tarifas locales de ejemplo, identificadas y repetibles para las seis canchas."""

from __future__ import annotations

from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import CommandError
from django.utils import timezone

from apps.canchas.models import Cancha
from apps.tarifas.models import ReglaTarifa, TipoTarifa
from apps.tarifas.services.validaciones import validar_regla_sin_ambiguedad
from apps.usuarios.services.datos_demo import MARCA, identidad_demo


def _proxima_fecha(dia_semana: int) -> date:
    hoy = timezone.localdate()
    diferencia = (dia_semana - hoy.weekday()) % 7 or 7
    return hoy + timedelta(days=diferencia)


def _actualizar_regla(
    cancha: Cancha, creador: User, clave: str, datos: dict
) -> None:
    nombre = f"{MARCA} {identidad_demo(f'tarifa-{clave}')}"
    coincidencias = list(ReglaTarifa.objects.filter(nombre=nombre)[:2])
    if len(coincidencias) > 1:
        raise CommandError(f"Hay tarifas demo duplicadas: {clave}.")
    existente = coincidencias[0] if coincidencias else None
    if existente and existente.cancha_id != cancha.pk:
        raise CommandError(f"La tarifa demo {clave} pertenece a otra cancha.")

    regla = existente or ReglaTarifa(cancha=cancha, creado_por=creador)
    valores = {"nombre": nombre, "cancha": cancha, "creado_por": creador, **datos}
    for campo, valor in valores.items():
        setattr(regla, campo, valor)
    regla.activa = True

    otras = ReglaTarifa.objects.filter(cancha=cancha, activa=True)
    if existente:
        otras = otras.exclude(pk=existente.pk)
    validar_regla_sin_ambiguedad(regla, list(otras))
    regla.save()


def crear_tarifas_demo(canchas: dict[str, Cancha], usuarios: dict[str, User]) -> None:
    """Crea ejemplos PEN; no configura tarifas fuera del seeder local autorizado."""
    hoy = timezone.localdate()
    proximo_feriado_demo = _proxima_fecha(0)
    proxima_fecha_especial = _proxima_fecha(4)
    valores_empresa = {
        "cancha_a_heredada": ("50.00", "70.00", "80.00"),
        "cancha_a_propia": ("55.00", "75.00", "85.00"),
        "cancha_a_norte": ("48.00", "68.00", "78.00"),
        "cancha_b_centro_1": ("45.00", "65.00", "75.00"),
        "cancha_b_centro_2": ("47.00", "67.00", "77.00"),
        "cancha_b_sur": ("42.00", "62.00", "72.00"),
    }
    creador = usuarios["superadmin"]
    for clave, (diurna, nocturna, fin_semana) in valores_empresa.items():
        cancha = canchas[clave]
        comunes = {"vigente_desde": hoy, "moneda": "PEN", "activa": True}
        _actualizar_regla(cancha, creador, f"{clave}-diurna", {
            **comunes, "tipo": TipoTarifa.DIURNA, "dias_semana": [0, 1, 2, 3, 4],
            "hora_inicio": time(15), "hora_fin": time(19), "todo_el_dia": False,
            "precio_hora": Decimal(diurna),
        })
        _actualizar_regla(cancha, creador, f"{clave}-nocturna", {
            **comunes, "tipo": TipoTarifa.NOCTURNA, "dias_semana": [0, 1, 2, 3, 4],
            "hora_inicio": time(19), "hora_fin": time(23), "todo_el_dia": False,
            "precio_hora": Decimal(nocturna),
        })
        _actualizar_regla(cancha, creador, f"{clave}-fin-semana", {
            **comunes, "tipo": TipoTarifa.FIN_SEMANA, "dias_semana": [],
            "hora_inicio": time(9), "hora_fin": time(23), "todo_el_dia": False,
            "precio_hora": Decimal(fin_semana),
        })

    for clave, tipo, fecha, precio in (
        ("cancha_a_heredada", TipoTarifa.FERIADO, proximo_feriado_demo, "100.00"),
        ("cancha_a_heredada", TipoTarifa.ESPECIAL, proxima_fecha_especial, "115.00"),
        ("cancha_b_centro_1", TipoTarifa.FERIADO, proximo_feriado_demo, "90.00"),
        ("cancha_b_centro_1", TipoTarifa.ESPECIAL, proxima_fecha_especial, "105.00"),
    ):
        _actualizar_regla(canchas[clave], creador, f"{clave}-{tipo}", {
            "tipo": tipo,
            "dias_semana": [],
            "fecha_aplicable_desde": fecha,
            "fecha_aplicable_hasta": fecha,
            "hora_inicio": time(15),
            "hora_fin": time(23),
            "todo_el_dia": False,
            "vigente_desde": hoy,
            "vigente_hasta": None,
            "precio_hora": Decimal(precio),
            "moneda": "PEN",
            "activa": True,
        })
