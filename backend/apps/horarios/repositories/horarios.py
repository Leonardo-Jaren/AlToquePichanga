from django.contrib.auth.models import User
from django.db.models import QuerySet

from apps.canchas.models import Cancha
from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.repositories.alcance import sedes_visibles
from apps.sedes.models import Sede


def sedes_con_horario_visible(usuario: User) -> QuerySet[Sede]:
    return sedes_visibles(usuario).select_related("empresa")


def canchas_con_horario_visible(usuario: User) -> QuerySet[Cancha]:
    return canchas_visibles(usuario)
