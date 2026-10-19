from typing import ClassVar

from django.db import models
from django.db.models import Q


class Sede(models.Model):
    empresa = models.ForeignKey("empresas.Empresa", on_delete=models.PROTECT, related_name="sedes")
    nombre = models.CharField(max_length=160)
    descripcion = models.TextField(blank=True)
    direccion = models.CharField(max_length=240)
    departamento = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=100, blank=True)
    distrito = models.CharField(max_length=100, blank=True)
    latitud = models.DecimalField(max_digits=8, decimal_places=6, null=True, blank=True)
    longitud = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    telefono_contacto = models.CharField(max_length=32, blank=True)
    whatsapp_contacto = models.CharField(max_length=32, blank=True)
    correo_contacto = models.EmailField(blank=True)
    horario_general = models.JSONField(default=dict, blank=True)
    imagen_principal = models.FileField(upload_to="sedes/portadas/", blank=True)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)
    actualizada_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sedes"
        ordering: ClassVar[list[str]] = ["nombre", "id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=(Q(latitud__isnull=True, longitud__isnull=True)
                           | Q(latitud__isnull=False, longitud__isnull=False)),
                name="sede_coordenadas_completas",
            ),
            models.CheckConstraint(
                condition=Q(latitud__isnull=True) | Q(latitud__gte=-90, latitud__lte=90),
                name="sede_latitud_valida",
            ),
            models.CheckConstraint(
                condition=Q(longitud__isnull=True) | Q(longitud__gte=-180, longitud__lte=180),
                name="sede_longitud_valida",
            ),
        ]


class AsignacionSede(models.Model):
    sede = models.ForeignKey(Sede, on_delete=models.PROTECT, related_name="asignaciones")
    membresia = models.ForeignKey(
        "empresas.MembresiaEmpresa", on_delete=models.PROTECT, related_name="sedes_asignadas"
    )
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sedes_asignaciones"
        constraints: ClassVar[list] = [
            models.UniqueConstraint(fields=["sede", "membresia"], name="sede_membresia_unica"),
        ]


class ImagenSede(models.Model):
    sede = models.ForeignKey(Sede, on_delete=models.PROTECT, related_name="imagenes")
    archivo = models.FileField(upload_to="sedes/galeria/")
    descripcion = models.CharField(max_length=180, blank=True)
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sedes_imagenes"
        ordering: ClassVar[list[str]] = ["orden", "id"]
