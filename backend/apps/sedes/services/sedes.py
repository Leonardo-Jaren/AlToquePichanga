from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.empresas.models import (
    AccesoPlataforma,
    Empresa,
    RegistroAuditoria,
)
from apps.empresas.repositories.alcance import sede_administrable, sedes_visibles
from apps.empresas.repositories.empresas import empresas_propietario
from apps.empresas.services.auditoria import auditar
from apps.reservas.services.eventos import programar_cambio_sede
from apps.sedes.models import ImagenSede, Sede
from apps.sedes.serializers import datos_imagen, datos_sede
from apps.suscripciones.services.reglas import empresa_con_cupo, suscripcion_operativa


def _empresa_nueva(usuario: User, identificador: int, bloquear: bool = False) -> Empresa:
    if usuario.is_superuser:
        consulta = Empresa.objects.all()
        if bloquear:
            consulta = consulta.select_for_update()
        return get_object_or_404(consulta, pk=identificador)
    empresas = empresas_propietario(usuario)
    if bloquear:
        empresas = empresas.select_for_update()
    return get_object_or_404(empresas, pk=identificador)


def _sede_visible(usuario: User, identificador: int) -> Sede:
    return get_object_or_404(
        sedes_visibles(usuario).select_related("empresa"),
        pk=identificador,
    )


def _puede_escribir(usuario: User, sede: Sede) -> bool:
    return sede_administrable(usuario, sede.pk)


def sede_editable(usuario: User, identificador: int) -> Sede:
    sede = _sede_visible(usuario, identificador)
    if not _puede_escribir(usuario, sede):
        raise PermissionDenied("No tienes acceso para modificar esta sede.")
    return sede


def _exigir_suscripcion(empresa: Empresa) -> None:
    if not suscripcion_operativa(empresa):
        raise PermissionDenied(
            "La empresa necesita una suscripción vigente y aprobación de plataforma."
        )


def listar_sedes(usuario: User, empresa_id: int | None = None) -> list[dict]:
    sedes = sedes_visibles(usuario).select_related("empresa")
    if empresa_id is not None:
        sedes = sedes.filter(empresa_id=empresa_id)
    if usuario.is_superuser:
        AccesoPlataforma.objects.create(usuario=usuario, accion="listar_sedes")
    return [datos_sede(sede) for sede in sedes.order_by("nombre", "id")]


@transaction.atomic
def crear_sede(usuario: User, datos: dict) -> dict:
    empresa = _empresa_nueva(usuario, datos["empresa_id"], bloquear=True)
    if not usuario.is_superuser:
        empresa_con_cupo(empresa.pk, "sede")
    sede = Sede.objects.create(
        empresa=empresa,
        **{campo: valor for campo, valor in datos.items() if campo != "empresa_id"},
    )
    auditar(usuario, "crear", "sede", sede.pk, empresa)
    return datos_sede(sede)


@transaction.atomic
def actualizar_sede(usuario: User, identificador: int, datos: dict) -> dict:
    sede = get_object_or_404(Sede.objects.select_for_update(), pk=identificador)
    if not _puede_escribir(usuario, sede):
        raise PermissionDenied("No tienes acceso para modificar esta sede.")
    if not usuario.is_superuser:
        _exigir_suscripcion(sede.empresa)
    campos = (
        "nombre", "descripcion", "direccion", "departamento", "provincia", "distrito",
        "latitud", "longitud", "telefono_contacto", "whatsapp_contacto",
        "correo_contacto", "horario_general", "imagen_principal",
    )
    cambios = {campo: datos[campo] for campo in campos if campo in datos}
    for campo, valor in cambios.items():
        setattr(sede, campo, valor)
    sede.save(update_fields=[*cambios, "actualizada_en"])
    auditar(usuario, "actualizar", "sede", sede.pk, sede.empresa, {"campos": sorted(cambios)})
    return datos_sede(sede)


@transaction.atomic
def cambiar_estado_sede(usuario: User, identificador: int, activa: bool) -> dict:
    sede = get_object_or_404(Sede.objects.select_for_update(), pk=identificador)
    if not _puede_escribir(usuario, sede):
        raise PermissionDenied("No tienes acceso para cambiar esta sede.")
    if sede.activa == activa:
        return datos_sede(sede)
    if activa and not usuario.is_superuser:
        empresa_con_cupo(sede.empresa_id, "sede")
    sede.activa = activa
    sede.save(update_fields=["activa", "actualizada_en"])
    auditar(
        usuario, "activar" if activa else "desactivar",
        "sede", sede.pk, sede.empresa,
    )
    programar_cambio_sede(sede.pk, "sede_actualizada")
    return datos_sede(sede)


@transaction.atomic
def agregar_imagen(usuario: User, identificador: int, datos: dict) -> dict:
    sede = _sede_visible(usuario, identificador)
    if not _puede_escribir(usuario, sede):
        raise PermissionDenied("No tienes acceso para modificar esta sede.")
    if not usuario.is_superuser:
        _exigir_suscripcion(sede.empresa)
    imagen = ImagenSede.objects.create(sede=sede, **datos)
    auditar(usuario, "agregar_imagen", "sede", sede.pk, sede.empresa,
            {"imagen_id": imagen.pk})
    return datos_imagen(imagen)


@transaction.atomic
def retirar_imagen(usuario: User, sede_id: int, imagen_id: int) -> dict:
    sede = _sede_visible(usuario, sede_id)
    if not _puede_escribir(usuario, sede):
        raise PermissionDenied("No tienes acceso para modificar esta sede.")
    imagen = get_object_or_404(
        ImagenSede.objects.select_for_update(),
        pk=imagen_id, sede=sede, activa=True,
    )
    imagen.activa = False
    imagen.save(update_fields=["activa"])
    auditar(usuario, "retirar_imagen", "sede", sede.pk, sede.empresa,
            {"imagen_id": imagen.pk})
    return {"id": imagen.pk, "activa": False}


def consultar_sede(usuario: User, identificador: int) -> dict:
    sede = _sede_visible(usuario, identificador)
    if usuario.is_superuser:
        RegistroAuditoria.objects.create(
            actor=usuario, empresa=sede.empresa, accion="consultar",
            recurso="sede", recurso_id=sede.pk,
        )
    return datos_sede(sede)
