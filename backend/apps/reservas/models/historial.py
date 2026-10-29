from typing import ClassVar

from django.conf import settings
from django.db import models

from .reserva import EstadoReserva


class HistorialEstadoReserva(models.Model):
    reserva = models.ForeignKey(
        "reservas.Reserva", on_delete=models.PROTECT, related_name="historial_estados"
    )
    estado_anterior = models.CharField(max_length=28, blank=True)
    estado_nuevo = models.CharField(max_length=28, choices=EstadoReserva.choices)
    motivo = models.CharField(max_length=240)
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cambios_estado_reserva",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reservas_historial_estados"
        ordering: ClassVar[list[str]] = ["creado_en", "id"]
