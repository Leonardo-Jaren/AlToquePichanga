from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q


class CondicionCancelacionSede(models.Model):
    sede = models.ForeignKey("sedes.Sede", on_delete=models.PROTECT, related_name="condiciones_cancelacion")
    version = models.PositiveIntegerField()
    texto = models.TextField()
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        db_table = "pagos_condiciones_cancelacion"
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["sede", "version"], name="condicion_sede_version_unica"),
            models.UniqueConstraint(fields=["sede"], condition=Q(activa=True), name="condicion_sede_activa_unica"),
        ]


class AceptacionCancelacion(models.Model):
    reserva = models.ForeignKey("reservas.Reserva", on_delete=models.PROTECT, related_name="aceptaciones_cancelacion")
    condicion = models.ForeignKey(CondicionCancelacionSede, on_delete=models.PROTECT)
    jugador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    texto_aceptado = models.TextField()
    version_aceptada = models.PositiveIntegerField()
    aceptada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "pagos_aceptaciones_cancelacion"
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["reserva", "condicion"], name="aceptacion_reserva_condicion_unica"),
        ]
