from typing import ClassVar

from django.db import models
from django.db.models import Q


class EstadoCancha(models.TextChoices):
    ACTIVA = "activa", "Activa"
    INACTIVA = "inactiva", "Inactiva"
    MANTENIMIENTO = "mantenimiento", "Mantenimiento"


class Cancha(models.Model):
    sede = models.ForeignKey(
        "sedes.Sede", on_delete=models.PROTECT, related_name="canchas"
    )
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    modalidad = models.PositiveSmallIntegerField()
    tipo_superficie = models.CharField(max_length=80)
    capacidad_jugadores = models.PositiveSmallIntegerField(null=True, blank=True)
    techada = models.BooleanField(default=False)
    iluminacion = models.BooleanField(default=False)
    caracteristicas = models.JSONField(default=list, blank=True)
    estado = models.CharField(
        max_length=16, choices=EstadoCancha.choices, default=EstadoCancha.ACTIVA
    )
    imagen_principal = models.FileField(
        upload_to="canchas/principales/", blank=True
    )
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "canchas"
        ordering: ClassVar[list[str]] = ["nombre", "id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(condition=Q(modalidad__gte=1), name="cancha_modalidad_positiva"),
            models.CheckConstraint(
                condition=Q(capacidad_jugadores__isnull=True)
                | Q(capacidad_jugadores__gte=1),
                name="cancha_capacidad_positiva",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoCancha.values), name="cancha_estado_valido"
            ),
        ]


class ImagenCancha(models.Model):
    cancha = models.ForeignKey(
        Cancha, on_delete=models.PROTECT, related_name="imagenes"
    )
    archivo = models.FileField(upload_to="canchas/galeria/")
    descripcion = models.CharField(max_length=180, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "canchas_imagenes"
        ordering: ClassVar[list[str]] = ["orden", "id"]
