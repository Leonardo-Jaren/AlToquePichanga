from django.contrib.auth.models import User
from django.db.models import Prefetch, QuerySet

from apps.canchas.models import Cancha, ImagenCancha
from apps.empresas.repositories.alcance import sedes_visibles


def canchas_visibles(usuario: User) -> QuerySet[Cancha]:
    sedes = sedes_visibles(usuario).values("id")
    imagenes = ImagenCancha.objects.filter(activa=True).order_by("orden", "id")
    return (
        Cancha.objects.filter(sede_id__in=sedes)
        .select_related("sede", "sede__empresa")
        .prefetch_related(Prefetch("imagenes", queryset=imagenes, to_attr="imagenes_activas"))
        .order_by("sede__nombre", "nombre", "id")
    )
