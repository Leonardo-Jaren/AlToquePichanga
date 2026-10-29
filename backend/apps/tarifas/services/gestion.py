from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.empresas.models import AccesoPlataforma
from apps.empresas.repositories.alcance import sede_administrable
from apps.empresas.services.auditoria import auditar
from apps.reservas.services.eventos import programar_cambio_disponibilidad
from apps.sedes.services.sedes import _exigir_suscripcion
from apps.tarifas.models import ReglaTarifa
from apps.tarifas.repositories.tarifas import cancha_tarifaria, reglas_de_cancha
from apps.tarifas.serializers import datos_regla_tarifa
from apps.tarifas.services.validaciones import validar_regla_sin_ambiguedad


def _cancha_editable(usuario: User, cancha_id: int, bloquear: bool = False):
    cancha = cancha_tarifaria(usuario, cancha_id, bloquear=bloquear)
    if not sede_administrable(usuario, cancha.sede_id):
        raise PermissionDenied("No tienes acceso para modificar las tarifas de esta cancha.")
    if not usuario.is_superuser:
        _exigir_suscripcion(cancha.sede.empresa)
    return cancha


def listar_tarifas(usuario: User, cancha_id: int) -> dict:
    cancha = cancha_tarifaria(usuario, cancha_id)
    if usuario.is_superuser:
        AccesoPlataforma.objects.create(usuario=usuario, accion="consultar_tarifas_cancha")
    reglas = reglas_de_cancha(cancha)
    return {
        "cancha_id": cancha.pk,
        "cancha": cancha.nombre,
        "sede_id": cancha.sede_id,
        "sede": cancha.sede.nombre,
        "empresa_id": cancha.sede.empresa_id,
        "empresa": cancha.sede.empresa.nombre_visible,
        "resultados": [datos_regla_tarifa(regla) for regla in reglas],
    }


@transaction.atomic
def crear_tarifa(usuario: User, cancha_id: int, datos: dict) -> dict:
    cancha = _cancha_editable(usuario, cancha_id, bloquear=True)
    regla = ReglaTarifa(cancha=cancha, creado_por=usuario, **datos)
    validar_regla_sin_ambiguedad(regla, list(reglas_de_cancha(cancha, solo_activas=True)))
    regla.save()
    auditar(usuario, "crear", "tarifa", regla.pk, cancha.sede.empresa, {
        "cancha_id": cancha.pk, "tipo": regla.tipo, "precio_hora": str(regla.precio_hora),
    })
    programar_cambio_disponibilidad(cancha.pk, None, "tarifa_actualizada")
    return datos_regla_tarifa(regla)


@transaction.atomic
def actualizar_tarifa(usuario: User, cancha_id: int, tarifa_id: int, datos: dict) -> dict:
    cancha = _cancha_editable(usuario, cancha_id, bloquear=True)
    regla = get_object_or_404(
        ReglaTarifa.objects.select_for_update(), pk=tarifa_id, cancha=cancha
    )
    cambios = {}
    for campo, valor in datos.items():
        if getattr(regla, campo) != valor:
            setattr(regla, campo, valor)
            cambios[campo] = valor
    validar_regla_sin_ambiguedad(
        regla, list(reglas_de_cancha(cancha, solo_activas=True))
    )
    if cambios:
        regla.save(update_fields=[*cambios, "actualizada_en"])
        auditar(usuario, "actualizar", "tarifa", regla.pk, cancha.sede.empresa, {
            "campos": sorted(cambios),
        })
        programar_cambio_disponibilidad(cancha.pk, None, "tarifa_actualizada")
    return datos_regla_tarifa(regla)


@transaction.atomic
def cambiar_estado_tarifa(
    usuario: User, cancha_id: int, tarifa_id: int, activa: bool
) -> dict:
    cancha = _cancha_editable(usuario, cancha_id, bloquear=True)
    regla = get_object_or_404(
        ReglaTarifa.objects.select_for_update(), pk=tarifa_id, cancha=cancha
    )
    if regla.activa == activa:
        return datos_regla_tarifa(regla)
    if activa:
        regla.activa = True
        validar_regla_sin_ambiguedad(
            regla, list(reglas_de_cancha(cancha, solo_activas=True))
        )
    else:
        regla.activa = False
    regla.save(update_fields=["activa", "actualizada_en"])
    auditar(
        usuario, "activar" if activa else "desactivar", "tarifa", regla.pk,
        cancha.sede.empresa, {"cancha_id": cancha.pk, "tipo": regla.tipo},
    )
    programar_cambio_disponibilidad(cancha.pk, None, "tarifa_actualizada")
    return datos_regla_tarifa(regla)
