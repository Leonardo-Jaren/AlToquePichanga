from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.canchas.models import Cancha, EstadoCancha
from apps.canchas.repositories.canchas import canchas_visibles
from apps.canchas.serializers import datos_cancha
from apps.empresas.models import AccesoPlataforma, RegistroAuditoria
from apps.empresas.repositories.alcance import sede_administrable, sedes_visibles
from apps.empresas.services.auditoria import auditar
from apps.sedes.services.sedes import _exigir_suscripcion
from apps.suscripciones.services.reglas import empresa_con_cupo


def _cancha_visible(usuario: User, cancha_id: int, bloquear: bool = False) -> Cancha:
    canchas = canchas_visibles(usuario)
    if bloquear:
        canchas = canchas.select_for_update(of=("self",))
    return get_object_or_404(canchas, pk=cancha_id)


def _cancha_editable(usuario: User, cancha_id: int, bloquear: bool = False) -> Cancha:
    cancha = _cancha_visible(usuario, cancha_id, bloquear)
    if not sede_administrable(usuario, cancha.sede_id):
        raise PermissionDenied("No tienes acceso para modificar esta cancha.")
    return cancha


def listar_canchas(usuario: User, filtros: dict) -> QuerySet[Cancha]:
    canchas = canchas_visibles(usuario)
    if "sede" in filtros:
        canchas = canchas.filter(sede_id=filtros["sede"])
    if "modalidad" in filtros:
        canchas = canchas.filter(modalidad=filtros["modalidad"])
    if filtros.get("estado"):
        canchas = canchas.filter(estado=filtros["estado"])
    if filtros.get("buscar"):
        canchas = canchas.filter(nombre__icontains=filtros["buscar"])
    if usuario.is_superuser:
        AccesoPlataforma.objects.create(usuario=usuario, accion="listar_canchas")
    return canchas


@transaction.atomic
def crear_cancha(usuario: User, datos: dict) -> dict:
    sedes = sedes_visibles(usuario).select_related("empresa")
    sede = get_object_or_404(sedes, pk=datos["sede_id"])
    if not sede_administrable(usuario, sede.pk):
        raise PermissionDenied("No tienes acceso para crear canchas en esta sede.")
    if not usuario.is_superuser:
        empresa_con_cupo(sede.empresa_id, "cancha")
    valores = {campo: valor for campo, valor in datos.items() if campo != "sede_id"}
    cancha = Cancha.objects.create(sede=sede, **valores)
    auditar(usuario, "crear", "cancha", cancha.pk, sede.empresa, {
        "sede_id": sede.pk, "modalidad": cancha.modalidad,
    })
    return datos_cancha(cancha)


@transaction.atomic
def actualizar_cancha(usuario: User, cancha_id: int, datos: dict) -> dict:
    cancha = _cancha_editable(usuario, cancha_id, bloquear=True)
    if not usuario.is_superuser:
        _exigir_suscripcion(cancha.sede.empresa)
    campos = (
        "nombre", "descripcion", "modalidad", "tipo_superficie", "capacidad_jugadores",
        "techada", "iluminacion", "caracteristicas", "imagen_principal",
    )
    cambios = {campo: datos[campo] for campo in campos if campo in datos}
    for campo, valor in cambios.items():
        setattr(cancha, campo, valor)
    cancha.save(update_fields=[*cambios, "actualizada_en"])
    auditar(usuario, "actualizar", "cancha", cancha.pk, cancha.sede.empresa, {
        "campos": sorted(cambios),
    })
    return datos_cancha(cancha)


@transaction.atomic
def cambiar_estado_cancha(usuario: User, cancha_id: int, estado: str) -> dict:
    cancha = _cancha_editable(usuario, cancha_id, bloquear=True)
    anterior = cancha.estado
    estados_ocupantes = {EstadoCancha.ACTIVA, EstadoCancha.MANTENIMIENTO}
    if anterior == estado:
        return datos_cancha(cancha)
    if anterior == EstadoCancha.INACTIVA and estado in estados_ocupantes:
        if not usuario.is_superuser:
            empresa_con_cupo(cancha.sede.empresa_id, "cancha")
    cancha.estado = estado
    cancha.save(update_fields=["estado", "actualizada_en"])
    auditar(usuario, "cambiar_estado", "cancha", cancha.pk, cancha.sede.empresa, {
        "anterior": anterior, "nuevo": estado,
    })
    return datos_cancha(cancha)


def consultar_cancha(usuario: User, cancha_id: int) -> dict:
    cancha = _cancha_visible(usuario, cancha_id)
    if usuario.is_superuser:
        RegistroAuditoria.objects.create(
            actor=usuario, empresa=cancha.sede.empresa, accion="consultar",
            recurso="cancha", recurso_id=cancha.pk,
        )
    return datos_cancha(cancha)


def cancha_editable(usuario: User, cancha_id: int) -> Cancha:
    return _cancha_editable(usuario, cancha_id)
