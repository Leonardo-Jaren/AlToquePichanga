from decimal import Decimal
from typing import ClassVar
from uuid import uuid4

from django.db import models
from django.db.models import Q


def generar_clave_pago() -> str:
    return uuid4().hex


class TipoPagoReserva(models.TextChoices):
    ADELANTO = "adelanto", "Adelanto mínimo"
    TOTAL = "total", "Pago total"
    SALDO = "saldo", "Saldo pendiente"


class EstadoPagoReserva(models.TextChoices):
    PENDIENTE_PAGO = "pendiente_pago", "Pendiente de pago"
    PENDIENTE_REVISION = "pendiente_revision", "Pendiente de revisión"
    APROBADO = "aprobado", "Aprobado manualmente"
    RECHAZADO = "rechazado", "Rechazado"
    VENCIDO = "vencido", "Vencido"
    PAGO_TARDIO = "pago_tardio", "Comprobante declarado fuera de plazo"


class PagoReserva(models.Model):
    reserva = models.ForeignKey("reservas.Reserva", on_delete=models.PROTECT, related_name="pagos_reserva")
    metodo = models.ForeignKey("pagos.MetodoPagoSede", on_delete=models.PROTECT, related_name="pagos")
    tipo = models.CharField(max_length=12, choices=TipoPagoReserva.choices)
    estado = models.CharField(
        max_length=24, choices=EstadoPagoReserva.choices, default=EstadoPagoReserva.PENDIENTE_PAGO
    )
    importe_solicitado = models.DecimalField(max_digits=10, decimal_places=2)
    importe_verificado = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    referencia = models.CharField(max_length=100, blank=True)
    observacion_jugador = models.CharField(max_length=240, blank=True)
    motivo_revision = models.CharField(max_length=240, blank=True)
    clave_idempotencia = models.UUIDField(default=uuid4, unique=True)
    requiere_conciliacion = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    declarado_en = models.DateTimeField(null=True, blank=True)
    revisado_en = models.DateTimeField(null=True, blank=True)
    revisor = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="pagos_reserva_revisados"
    )

    class Meta:
        db_table = "reservas_pagos"
        ordering: ClassVar[list[str]] = ["-creado_en", "-id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=Q(importe_solicitado__gt=Decimal("0.00"))
                & Q(importe_verificado__gte=Decimal("0.00")),
                name="pago_reserva_importes_no_negativos",
            ),
            models.CheckConstraint(condition=Q(tipo__in=TipoPagoReserva.values), name="pago_reserva_tipo_valido"),
            models.CheckConstraint(condition=Q(estado__in=EstadoPagoReserva.values), name="pago_reserva_estado_valido"),
            models.UniqueConstraint(
                fields=["reserva"],
                condition=Q(estado__in=[EstadoPagoReserva.PENDIENTE_PAGO, EstadoPagoReserva.PENDIENTE_REVISION]),
                name="reserva_un_pago_pendiente",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.reserva.codigo} · {self.get_tipo_display()}"
