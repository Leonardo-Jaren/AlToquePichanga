from typing import ClassVar

from django.conf import settings
from django.db import models


class HistorialPagoReserva(models.Model):
    pago = models.ForeignKey("pagos.PagoReserva", on_delete=models.PROTECT, related_name="historial")
    estado_anterior = models.CharField(max_length=24, blank=True)
    estado_nuevo = models.CharField(max_length=24)
    motivo = models.CharField(max_length=240)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="cambios_pago_reserva",
    )
    datos = models.JSONField(default=dict, blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reservas_historial_pagos"
        ordering: ClassVar[list[str]] = ["creado_en", "id"]
