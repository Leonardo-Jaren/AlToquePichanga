from typing import ClassVar

from django.db import models
from django.db.models import Q


class TipoMetodoPago(models.TextChoices):
    YAPE = "yape", "Yape"
    PLIN = "plin", "Plin"
    TRANSFERENCIA = "transferencia", "Transferencia bancaria"


class MetodoPagoSede(models.Model):
    sede = models.ForeignKey("sedes.Sede", on_delete=models.PROTECT, related_name="medios_pago")
    tipo = models.CharField(max_length=20, choices=TipoMetodoPago.choices)
    titular = models.CharField(max_length=160)
    numero_cuenta = models.CharField(max_length=40, blank=True)
    banco = models.CharField(max_length=100, blank=True)
    cci = models.CharField(max_length=24, blank=True)
    imagen_qr = models.FileField(upload_to="pagos/qr/", blank=True)
    instrucciones = models.CharField(max_length=240, blank=True)
    activo = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sedes_metodos_pago"
        ordering: ClassVar[list[str]] = ["tipo", "id"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["sede", "tipo"], name="metodo_pago_sede_tipo_unico"),
            models.CheckConstraint(condition=Q(tipo__in=TipoMetodoPago.values), name="metodo_pago_tipo_valido"),
        ]

    def __str__(self) -> str:
        return f"{self.get_tipo_display()} · {self.sede.nombre}"
