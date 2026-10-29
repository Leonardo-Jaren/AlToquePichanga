from django.db.models import Prefetch, QuerySet
from django.shortcuts import get_object_or_404

from apps.canchas.models import Cancha, EstadoCancha, ImagenCancha


def canchas_publicadas() -> QuerySet[Cancha]:
    imagenes = ImagenCancha.objects.filter(activa=True).order_by("orden", "id")
    return (
        Cancha.objects.filter(
            publicada=True,
            estado__in=(EstadoCancha.ACTIVA, EstadoCancha.MANTENIMIENTO),
            sede__activa=True,
            sede__empresa__activa=True,
        )
        .select_related("sede")
        .prefetch_related(Prefetch("imagenes", queryset=imagenes, to_attr="imagenes_activas"))
        .order_by("sede__nombre", "nombre", "id")
    )


def cancha_publicada(cancha_id: int) -> Cancha:
    return get_object_or_404(canchas_publicadas(), pk=cancha_id)


def datos_cancha_publica(cancha: Cancha) -> dict:
    """Lista solo datos definidos para mostrar a cualquier visitante."""
    imagenes = getattr(cancha, "imagenes_activas", ())
    return {
        "id": cancha.pk,
        "nombre": cancha.nombre,
        "descripcion": cancha.descripcion,
        "modalidad": cancha.modalidad,
        "tipo_superficie": cancha.tipo_superficie,
        "capacidad_jugadores": cancha.capacidad_jugadores,
        "techada": cancha.techada,
        "iluminacion": cancha.iluminacion,
        "caracteristicas": cancha.caracteristicas,
        "estado": cancha.estado,
        "imagen_principal_url": cancha.imagen_principal.url if cancha.imagen_principal else None,
        "imagenes": [{
            "id": imagen.pk,
            "url": imagen.archivo.url,
            "descripcion": imagen.descripcion,
            "orden": imagen.orden,
        } for imagen in imagenes],
        "sede": {
            "nombre": cancha.sede.nombre,
            "distrito": cancha.sede.distrito,
            "provincia": cancha.sede.provincia,
            "departamento": cancha.sede.departamento,
        },
    }
