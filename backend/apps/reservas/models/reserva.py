from decimal import Decimal
from typing import ClassVar
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import Q


def generar_codigo_reserva() -> str:
    return f"ATP-{uuid4().hex[:12].upper()}"


class EstadoReserva(models.TextChoices):
    RETENIDA = "retenida", "Retenida temporalmente"
    PENDIENTE_PAGO = "pendiente_pago", "Pendiente de pago"
    PENDIENTE_VERIFICACION = "pendiente_verificacion", "Pendiente de verificación"
    PENDIENTE_CONFIRMACION = "pendiente_confirmacion", "Pago aprobado, pendiente de confirmación"
    CONFIRMADA = "confirmada", "Confirmada"
    VENCIDA = "vencida", "Vencida"
    CANCELADA = "cancelada", "Cancelada"
    RECHAZADA = "rechazada", "Rechazada"
    FINALIZADA = "finalizada", "Finalizada"


class Reserva(models.Model):
    codigo = models.CharField(max_length=16, unique=True, default=generar_codigo_reserva)
    jugador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservas"
    )
    cancha = models.ForeignKey(
        "canchas.Cancha", on_delete=models.PROTECT, related_name="reservas"
    )
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    duracion_horas = models.PositiveSmallIntegerField()
    importe_total = models.DecimalField(max_digits=10, decimal_places=2)
    adelanto_minimo = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, default="PEN")
    estado = models.CharField(
        max_length=28, choices=EstadoReserva.choices, default=EstadoReserva.RETENIDA
    )
    retencion_vence_en = models.DateTimeField()
    revision_pago_vence_en = models.DateTimeField(null=True, blank=True)
    revision_pago_extendida = models.BooleanField(default=False)
    cotizacion_aplicada = models.JSONField(default=dict)
    clave_idempotencia = models.UUIDField()
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reservas"
        ordering: ClassVar[list[str]] = ["-creada_en", "-id"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["jugador", "clave_idempotencia"], name="reserva_idempotencia_jugador"
            ),
            models.CheckConstraint(condition=Q(fin__gt=models.F("inicio")), name="reserva_intervalo_positivo"),
            models.CheckConstraint(
                condition=Q(duracion_horas__gte=1, duracion_horas__lte=24),
                name="reserva_duracion_valida",
            ),
            models.CheckConstraint(
                condition=Q(importe_total__gt=Decimal("0.00"))
                & Q(adelanto_minimo__gte=Decimal("0.00"))
                & Q(adelanto_minimo__lte=models.F("importe_total")),
                name="reserva_importes_validos",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoReserva.values), name="reserva_estado_valido"
            ),
        ]

    def __str__(self) -> str:
        return self.codigo
