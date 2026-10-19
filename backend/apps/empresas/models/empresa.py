from typing import ClassVar

from django.conf import settings
from django.db import models
from django.db.models import Q


class EstadoEmpresa(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente de aprobación"
    ACTIVA = "activa", "Activa"
    RECHAZADA = "rechazada", "Rechazada"
    SUSPENDIDA = "suspendida", "Suspendida"


class Empresa(models.Model):
    nombre = models.CharField(max_length=160)
    razon_social = models.CharField(max_length=180, blank=True)
    nombre_comercial = models.CharField(max_length=160, blank=True)
    ruc = models.CharField(max_length=11, blank=True)
    descripcion = models.TextField(blank=True)
    logotipo = models.FileField(upload_to="empresas/logotipos/", blank=True)
    correo_contacto = models.EmailField(blank=True)
    telefono_contacto = models.CharField(max_length=32, blank=True)
    direccion_administrativa = models.CharField(max_length=240, blank=True)
    estado = models.CharField(
        max_length=16, choices=EstadoEmpresa.choices, default=EstadoEmpresa.ACTIVA
    )
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "empresas"
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["ruc"], condition=~Q(ruc=""), name="empresa_ruc_unico"
            ),
        ]

    def save(self, *args, **kwargs):
        campos = kwargs.get("update_fields")
        if campos is not None and "activa" in campos and "estado" not in campos:
            if self.estado not in (EstadoEmpresa.PENDIENTE, EstadoEmpresa.RECHAZADA):
                self.estado = EstadoEmpresa.ACTIVA if self.activa else EstadoEmpresa.SUSPENDIDA
            kwargs["update_fields"] = {*campos, "estado"}
        super().save(*args, **kwargs)

    @property
    def nombre_visible(self) -> str:
        return self.nombre_comercial or self.nombre


class RolEmpresa(models.TextChoices):
    DUENO = "dueno", "Dueño de empresa"
    ADMINISTRADOR_SEDE = "administrador_sede", "Administrador de sede"
    CAJERO = "cajero", "Cajero / Empleado"


class MembresiaEmpresa(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="membresias"
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="membresias")
    rol = models.CharField(max_length=24, choices=RolEmpresa.choices)
    activa = models.BooleanField(default=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "empresas_membresias"
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["usuario", "empresa", "rol"], name="membresia_rol_unico"
            ),
            models.CheckConstraint(
                condition=models.Q(rol__in=RolEmpresa.values), name="membresia_rol_valido"
            ),
        ]


class AccesoPlataforma(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    empresa = models.ForeignKey(Empresa, on_delete=models.PROTECT, null=True)
    accion = models.CharField(max_length=80)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "empresas_accesos_plataforma"
