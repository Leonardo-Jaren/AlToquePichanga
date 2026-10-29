from typing import ClassVar

from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import (
    DateTimeRangeField,
    RangeBoundary,
    RangeOperators,
)
from django.db import models
from django.db.models import F, Func, Q


class TsTzRange(Func):
    function = "TSTZRANGE"
    output_field = DateTimeRangeField()


class BloqueReserva(models.Model):
    reserva = models.ForeignKey(
        "reservas.Reserva", on_delete=models.PROTECT, related_name="bloques"
    )
    cancha = models.ForeignKey(
        "canchas.Cancha", on_delete=models.PROTECT, related_name="bloques_reservados"
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    liberado_en = models.DateTimeField(null=True, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reservas_bloques"
        ordering: ClassVar[list[str]] = ["inicio", "id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(condition=Q(fin__gt=F("inicio")), name="bloque_reserva_intervalo_positivo"),
            ExclusionConstraint(
                name="bloque_cancha_sin_solapamiento_activo",
                expressions=[
                    ("cancha", RangeOperators.EQUAL),
                    (
                        TsTzRange(
                            "inicio", "fin",
                            RangeBoundary(inclusive_lower=True, inclusive_upper=False),
                        ),
                        RangeOperators.OVERLAPS,
                    ),
                ],
                condition=Q(liberado_en__isnull=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.cancha_id}: {self.inicio:%Y-%m-%d %H:%M}"
