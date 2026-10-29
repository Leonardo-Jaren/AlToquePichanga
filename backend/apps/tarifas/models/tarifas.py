from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q


class TipoTarifa(models.TextChoices):
    DIURNA = "diurna", "Diurna"
    NOCTURNA = "nocturna", "Nocturna"
    FIN_SEMANA = "fin_semana", "Fin de semana"
    FERIADO = "feriado", "Feriado"
    ESPECIAL = "especial", "Fecha especial"


class ReglaTarifa(models.Model):
    cancha = models.ForeignKey(
        "canchas.Cancha", on_delete=models.PROTECT, related_name="reglas_tarifa"
    )
    tipo = models.CharField(max_length=16, choices=TipoTarifa.choices)
    nombre = models.CharField(max_length=120, blank=True)
    dias_semana = models.JSONField(default=list, blank=True)
    fecha_aplicable_desde = models.DateField(null=True, blank=True)
    fecha_aplicable_hasta = models.DateField(null=True, blank=True)
    hora_inicio = models.TimeField(null=True, blank=True)
    hora_fin = models.TimeField(null=True, blank=True)
    todo_el_dia = models.BooleanField(default=False)
    vigente_desde = models.DateField()
    vigente_hasta = models.DateField(null=True, blank=True)
    precio_hora = models.DecimalField(max_digits=10, decimal_places=2)
    moneda = models.CharField(max_length=3, choices=[("PEN", "PEN")], default="PEN")
    activa = models.BooleanField(default=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="reglas_tarifa_creadas",
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "tarifas_reglas"
        ordering: ClassVar[list[str]] = ["tipo", "vigente_desde", "hora_inicio", "id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=Q(precio_hora__gt=0), name="tarifa_precio_positivo",
            ),
            models.CheckConstraint(
                condition=Q(vigente_hasta__isnull=True)
                | Q(vigente_hasta__gte=models.F("vigente_desde")),
                name="tarifa_vigencia_ordenada",
            ),
            models.CheckConstraint(
                condition=Q(fecha_aplicable_desde__isnull=True)
                | Q(fecha_aplicable_hasta__isnull=True)
                | Q(fecha_aplicable_hasta__gte=models.F("fecha_aplicable_desde")),
                name="tarifa_fechas_ordenadas",
            ),
            models.CheckConstraint(
                condition=(
                    Q(todo_el_dia=True, hora_inicio__isnull=True, hora_fin__isnull=True)
                    | Q(
                        todo_el_dia=False,
                        hora_inicio__isnull=False,
                        hora_fin__isnull=False,
                    ) & ~Q(hora_inicio=models.F("hora_fin"))
                ),
                name="tarifa_rango_horas_valido",
            ),
            models.CheckConstraint(
                condition=Q(tipo__in=TipoTarifa.values), name="tarifa_tipo_valido",
            ),
            models.CheckConstraint(condition=Q(moneda="PEN"), name="tarifa_moneda_pen"),
            models.UniqueConstraint(
                fields=["cancha", "nombre"], condition=~Q(nombre=""),
                name="tarifa_nombre_cancha_unico",
            ),
        ]

