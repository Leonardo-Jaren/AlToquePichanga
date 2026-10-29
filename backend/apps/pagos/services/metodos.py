from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied

from apps.empresas.repositories.alcance import sede_administrable, sedes_visibles
from apps.empresas.services.auditoria import auditar
from apps.pagos.models import MetodoPagoSede
from apps.sedes.models import Sede


def _sede_visible(usuario, sede_id: int) -> Sede:
    return get_object_or_404(sedes_visibles(usuario).select_related("empresa"), pk=sede_id)


def listar_metodos_personal(usuario, sede_id: int) -> list[MetodoPagoSede]:
    sede = _sede_visible(usuario, sede_id)
    metodos = MetodoPagoSede.objects.filter(sede=sede)
    if not usuario.is_superuser and not sede_administrable(usuario, sede.pk):
        metodos = metodos.filter(activo=True)
    if usuario.is_superuser:
        auditar(usuario, "consultar_metodos_pago_global", "metodos_pago", sede.pk, sede.empresa)
    return list(metodos.order_by("tipo", "id"))


@transaction.atomic
def guardar_metodo(usuario, sede_id: int, datos: dict) -> MetodoPagoSede:
    sede = Sede.objects.select_for_update().select_related("empresa").filter(pk=sede_id).first()
    if sede is None or not sede_administrable(usuario, sede_id) or usuario.is_superuser:
        raise PermissionDenied("Solo el dueño o administrador de la sede puede configurar sus medios de pago.")
    metodo = MetodoPagoSede.objects.select_for_update().filter(
        sede=sede, tipo=datos["tipo"],
    ).first()
    archivo = datos.pop("imagen_qr", None)
    if metodo is None:
        metodo = MetodoPagoSede(sede=sede, **datos)
    else:
        for campo, valor in datos.items():
            setattr(metodo, campo, valor)
    if archivo is not None:
        metodo.imagen_qr = archivo
    metodo.save()
    auditar(
        usuario, "configurar_medio_pago", "metodo_pago", metodo.pk, sede.empresa,
        {"sede_id": sede.pk, "tipo": metodo.tipo, "activo": metodo.activo},
    )
    return metodo
