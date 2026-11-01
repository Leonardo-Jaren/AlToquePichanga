from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.empresas.repositories.alcance import sede_administrable, sedes_visibles
from apps.empresas.services.auditoria import auditar
from apps.pagos.models import AceptacionCancelacion, CondicionCancelacionSede
from apps.sedes.models import Sede


def condicion_actual(sede_id: int):
    return CondicionCancelacionSede.objects.filter(sede_id=sede_id, activa=True).first()


def datos_condicion(condicion):
    return {"version": condicion.version, "texto": condicion.texto} if condicion else None


def consultar_condicion(usuario, sede_id: int):
    sede = get_object_or_404(sedes_visibles(usuario).select_related("empresa"), pk=sede_id)
    if usuario.is_superuser:
        auditar(usuario, "consultar_condiciones_global", "sede", sede.pk, sede.empresa)
    return datos_condicion(condicion_actual(sede_id))


@transaction.atomic
def publicar_condicion(usuario, sede_id: int, texto: str):
    sede = get_object_or_404(Sede.objects.select_for_update().select_related("empresa"), pk=sede_id)
    if usuario.is_superuser or not sede_administrable(usuario, sede_id):
        raise PermissionDenied("Solo el dueño o administrador autorizado puede configurar las condiciones de su sede.")
    anterior = condicion_actual(sede_id)
    if anterior and anterior.texto == texto:
        return anterior
    version = anterior.version + 1 if anterior else 1
    if anterior:
        anterior.activa = False
        anterior.save(update_fields=["activa"])
    nueva = CondicionCancelacionSede.objects.create(sede=sede, texto=texto, version=version, creada_por=usuario)
    auditar(usuario, "publicar_condicion_cancelacion", "sede", sede.pk, sede.empresa, {"version": version})
    return nueva


def registrar_aceptacion(reserva, jugador, version: int, aceptada: bool) -> None:
    Sede.objects.select_for_update().get(pk=reserva.cancha.sede_id)
    condicion = condicion_actual(reserva.cancha.sede_id)
    if condicion is None:
        raise ValidationError({"condiciones": "La sede aún no configuró sus condiciones de cancelación."})
    if not aceptada or condicion.version != version:
        raise ValidationError({"condiciones": "Lee y acepta la versión vigente de las condiciones de la sede."})
    AceptacionCancelacion.objects.get_or_create(
        reserva=reserva, condicion=condicion,
        defaults={"jugador": jugador, "texto_aceptado": condicion.texto, "version_aceptada": condicion.version},
    )
