from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q


class HorarioSede(models.Model):
    sede = models.OneToOneField(
        "sedes.Sede", on_delete=models.PROTECT, related_name="horario_semanal"
    )
    configurado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "horarios_sede"


class IntervaloHorarioSede(models.Model):
    horario = models.ForeignKey(
        HorarioSede, on_delete=models.CASCADE, related_name="intervalos"
    )
    dia_semana = models.PositiveSmallIntegerField()
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()

    class Meta:
        db_table = "horarios_sede_intervalos"
        ordering: ClassVar[list[str]] = ["dia_semana", "hora_apertura", "id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=Q(dia_semana__gte=0, dia_semana__lte=6),
                name="horario_sede_dia_0_6",
            ),
            models.CheckConstraint(
                condition=~Q(hora_apertura=models.F("hora_cierre")),
                name="horario_sede_horas_distintas",
            ),
        ]


class HorarioCancha(models.Model):
    cancha = models.OneToOneField(
        "canchas.Cancha", on_delete=models.PROTECT, related_name="horario_semanal"
    )
    hereda_horario_sede = models.BooleanField(default=True)
    dias_heredados = models.JSONField(default=list, blank=True)
    configurado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "horarios_cancha"


class IntervaloHorarioCancha(models.Model):
    horario = models.ForeignKey(
        HorarioCancha, on_delete=models.CASCADE, related_name="intervalos"
    )
    dia_semana = models.PositiveSmallIntegerField()
    hora_apertura = models.TimeField()
    hora_cierre = models.TimeField()

    class Meta:
        db_table = "horarios_cancha_intervalos"
        ordering: ClassVar[list[str]] = ["dia_semana", "hora_apertura", "id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=Q(dia_semana__gte=0, dia_semana__lte=6),
                name="horario_cancha_dia_0_6",
            ),
            models.CheckConstraint(
                condition=~Q(hora_apertura=models.F("hora_cierre")),
                name="horario_cancha_horas_distintas",
            ),
        ]


class TipoExcepcionHorario(models.TextChoices):
    CIERRE = "cierre", "Cierre"
    AMPLIACION = "ampliacion", "Ampliación"


class ExcepcionHorario(models.Model):
    sede = models.ForeignKey(
        "sedes.Sede", on_delete=models.PROTECT, related_name="excepciones_horario"
    )
    cancha = models.ForeignKey(
        "canchas.Cancha", null=True, blank=True, on_delete=models.PROTECT,
        related_name="excepciones_horario",
    )
    tipo = models.CharField(max_length=12, choices=TipoExcepcionHorario.choices)
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    motivo = models.CharField(max_length=300)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="excepciones_horario_creadas"
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    anulada = models.BooleanField(default=False)
    anulada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="excepciones_horario_anuladas",
    )
    anulada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "horarios_excepciones"
        ordering: ClassVar[list[str]] = ["fecha_inicio", "id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=Q(fecha_fin__gt=models.F("fecha_inicio")),
                name="excepcion_horario_fin_posterior",
            ),
            models.CheckConstraint(
                condition=(Q(anulada=False, anulada_por__isnull=True, anulada_en__isnull=True)
                           | Q(anulada=True, anulada_por__isnull=False, anulada_en__isnull=False)),
                name="excepcion_horario_anulacion_consistente",
            ),
            models.CheckConstraint(
                condition=Q(tipo__in=TipoExcepcionHorario.values),
                name="excepcion_horario_tipo_valido",
            ),
        ]
