from django.contrib.auth.models import User
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from apps.canchas.models import Cancha
from apps.canchas.repositories.canchas import canchas_visibles
from apps.tarifas.models import ReglaTarifa


def cancha_tarifaria(
    usuario: User, cancha_id: int, *, bloquear: bool = False
) -> Cancha:
    canchas = canchas_visibles(usuario)
    if bloquear:
        canchas = canchas.select_for_update(of=("self",))
    return get_object_or_404(canchas, pk=cancha_id)


def reglas_de_cancha(cancha: Cancha, *, solo_activas: bool = False) -> QuerySet[ReglaTarifa]:
    reglas = ReglaTarifa.objects.filter(cancha=cancha).select_related("creado_por")
    if solo_activas:
        reglas = reglas.filter(activa=True)
    return reglas.order_by("tipo", "vigente_desde", "hora_inicio", "id")

