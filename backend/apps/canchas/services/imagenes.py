from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.canchas.models import Cancha, ImagenCancha
from apps.canchas.serializers import datos_cancha
from apps.canchas.services.canchas import _cancha_editable
from apps.empresas.services.auditoria import auditar
from apps.sedes.services.sedes import _exigir_suscripcion


def _refrescar_imagenes_activas(cancha: Cancha) -> None:
    cancha.imagenes_activas = list(
        cancha.imagenes.filter(activa=True).order_by("orden", "id")
    )


@transaction.atomic
def agregar_imagen(usuario: User, cancha_id: int, datos: dict) -> dict:
    cancha = _cancha_editable(usuario, cancha_id, bloquear=True)
    if not usuario.is_superuser:
        _exigir_suscripcion(cancha.sede.empresa)
    principal = datos.pop("principal", False)
    imagen = ImagenCancha.objects.create(cancha=cancha, **datos)
    if principal or not cancha.imagen_principal:
        cancha.imagen_principal = imagen.archivo.name
        cancha.save(update_fields=["imagen_principal", "actualizada_en"])
    _refrescar_imagenes_activas(cancha)
    auditar(usuario, "agregar_imagen", "cancha", cancha.pk, cancha.sede.empresa, {
        "imagen_id": imagen.pk, "principal": principal,
    })
    return datos_cancha(cancha)


@transaction.atomic
def retirar_imagen(usuario: User, cancha_id: int, imagen_id: int) -> dict:
    cancha = _cancha_editable(usuario, cancha_id, bloquear=True)
    imagen = get_object_or_404(
        ImagenCancha.objects.select_for_update(),
        pk=imagen_id, cancha=cancha, activa=True,
    )
    imagen.activa = False
    imagen.save(update_fields=["activa"])
    if cancha.imagen_principal.name == imagen.archivo.name:
        reemplazo = cancha.imagenes.filter(activa=True).exclude(pk=imagen.pk).order_by(
            "orden", "id"
        ).first()
        cancha.imagen_principal = reemplazo.archivo.name if reemplazo else ""
        cancha.save(update_fields=["imagen_principal", "actualizada_en"])
    _refrescar_imagenes_activas(cancha)
    auditar(usuario, "retirar_imagen", "cancha", cancha.pk, cancha.sede.empresa, {
        "imagen_id": imagen.pk,
    })
    return datos_cancha(cancha)
