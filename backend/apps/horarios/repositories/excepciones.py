from django.contrib.auth.models import User
from django.db.models import QuerySet

from apps.empresas.repositories.alcance import sedes_visibles
from apps.horarios.models import ExcepcionHorario


def excepciones_visibles(
    usuario: User,
    sede_id: int | None = None,
    cancha_id: int | None = None,
) -> QuerySet[ExcepcionHorario]:
    sedes = sedes_visibles(usuario).values("id")
    consulta = ExcepcionHorario.objects.filter(sede_id__in=sedes).select_related(
        "sede", "sede__empresa", "cancha", "creado_por", "anulada_por"
    )
    if sede_id is not None:
        consulta = consulta.filter(sede_id=sede_id)
    if cancha_id is not None:
        consulta = consulta.filter(cancha_id=cancha_id)
    return consulta.order_by("fecha_inicio", "id")
