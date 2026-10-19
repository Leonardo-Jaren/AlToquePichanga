from typing import ClassVar

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class FrecuenciaSuscripcion(models.TextChoices):
    MENSUAL = "mensual", "Mensual"
    TRIMESTRAL = "trimestral", "Trimestral"
    SEMESTRAL = "semestral", "Semestral"
    ANUAL = "anual", "Anual"


class EstadoSuscripcion(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente"
    ACTIVA = "activa", "Activa"
    VENCIDA = "vencida", "Vencida"
    SUSPENDIDA = "suspendida", "Suspendida"
    CANCELADA = "cancelada", "Cancelada"


class EstadoSolicitud(models.TextChoices):
    PENDIENTE = "pendiente", "Pendiente de revisión"
    APROBADA = "aprobada", "Aprobada"
    RECHAZADA = "rechazada", "Rechazada"


class TipoSolicitud(models.TextChoices):
    ACTIVACION = "activacion", "Activación"
    RENOVACION = "renovacion", "Renovación"


class PlanSuscripcion(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    moneda = models.CharField(
        max_length=3, default="PEN",
        validators=[RegexValidator(r"^[A-Z]{3}$", "Usa un código ISO de tres letras.")],
    )
    frecuencia = models.CharField(max_length=16, choices=FrecuenciaSuscripcion.choices)
    maximo_sedes = models.PositiveIntegerField(null=True, blank=True)
    maximo_empleados = models.PositiveIntegerField(null=True, blank=True)
    maximo_canchas = models.PositiveIntegerField(null=True, blank=True)
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suscripciones_planes"
        ordering: ClassVar[list[str]] = ["precio", "nombre"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(condition=Q(precio__gte=0), name="plan_precio_no_negativo"),
            models.UniqueConstraint(Lower("nombre"), name="plan_nombre_unico"),
        ]


class SuscripcionEmpresa(models.Model):
    empresa = models.OneToOneField(
        "empresas.Empresa", on_delete=models.PROTECT, related_name="suscripcion"
    )
    plan = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT, related_name="suscripciones")
    estado = models.CharField(max_length=16, choices=EstadoSuscripcion.choices)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)
    importe_acordado = models.DecimalField(max_digits=12, decimal_places=2)
    moneda_acordada = models.CharField(max_length=3)
    frecuencia_acordada = models.CharField(max_length=16, choices=FrecuenciaSuscripcion.choices)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suscripciones_empresas"


class PeriodoSuscripcion(models.Model):
    suscripcion = models.ForeignKey(
        SuscripcionEmpresa, on_delete=models.PROTECT, related_name="periodos"
    )
    plan = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT, related_name="periodos")
    fecha_inicio = models.DateField()
    fecha_vencimiento = models.DateField()
    importe_acordado = models.DecimalField(max_digits=12, decimal_places=2)
    moneda_acordada = models.CharField(max_length=3)
    frecuencia_acordada = models.CharField(max_length=16, choices=FrecuenciaSuscripcion.choices)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suscripciones_periodos"
        ordering: ClassVar[list[str]] = ["-fecha_inicio", "-id"]
        constraints: ClassVar[list] = [
            models.CheckConstraint(
                condition=Q(fecha_vencimiento__gte=models.F("fecha_inicio")),
                name="periodo_suscripcion_fechas_validas",
            ),
        ]


class SolicitudSuscripcion(models.Model):
    empresa = models.ForeignKey(
        "empresas.Empresa", on_delete=models.PROTECT, related_name="solicitudes_suscripcion"
    )
    plan = models.ForeignKey(PlanSuscripcion, on_delete=models.PROTECT, related_name="solicitudes")
    tipo = models.CharField(max_length=12, choices=TipoSolicitud.choices)
    estado = models.CharField(
        max_length=12, choices=EstadoSolicitud.choices, default=EstadoSolicitud.PENDIENTE
    )
    precio_solicitado = models.DecimalField(max_digits=12, decimal_places=2)
    moneda_solicitada = models.CharField(max_length=3)
    frecuencia_solicitada = models.CharField(max_length=16, choices=FrecuenciaSuscripcion.choices)
    medio_declarado = models.CharField(max_length=40, blank=True)
    referencia_declarada = models.CharField(max_length=120, blank=True)
    nota = models.CharField(max_length=500, blank=True)
    solicitada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="solicitudes_suscripcion"
    )
    revisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
        related_name="solicitudes_suscripcion_revisadas",
    )
    revisada_en = models.DateTimeField(null=True, blank=True)
    creada_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suscripciones_solicitudes"
        ordering: ClassVar[list[str]] = ["-creada_en", "-id"]
        constraints: ClassVar[list] = [
            models.UniqueConstraint(
                fields=["empresa"], condition=Q(estado=EstadoSolicitud.PENDIENTE),
                name="solicitud_suscripcion_pendiente_unica",
            ),
            models.CheckConstraint(
                condition=Q(precio_solicitado__gte=0), name="solicitud_precio_no_negativo"
            ),
        ]


class PagoSuscripcion(models.Model):
    solicitud = models.OneToOneField(
        SolicitudSuscripcion, on_delete=models.PROTECT, related_name="pago_verificado"
    )
    importe_verificado = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=3)
    referencia = models.CharField(max_length=120, blank=True)
    medio = models.CharField(max_length=40, blank=True)
    confirmado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    confirmado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suscripciones_pagos"
        constraints: ClassVar[list] = [
            models.CheckConstraint(condition=Q(importe_verificado__gte=0), name="pago_saas_no_negativo"),
        ]


class ConfiguracionSuscripcion(models.Model):
    dias_gracia = models.PositiveSmallIntegerField(default=0)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "suscripciones_configuracion"
