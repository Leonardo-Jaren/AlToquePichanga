from decimal import Decimal

from django.db.models.functions import Lower
from rest_framework import serializers

from apps.empresas.serializers import EntradaEstricta
from apps.suscripciones.models import FrecuenciaSuscripcion, PlanSuscripcion


class PlanEntrada(EntradaEstricta):
    nombre = serializers.CharField(max_length=100, required=False)
    descripcion = serializers.CharField(max_length=4000, allow_blank=True, required=False)
    precio = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False)
    moneda = serializers.RegexField(r"^[A-Z]{3}$", max_length=3, required=False)
    frecuencia = serializers.ChoiceField(choices=FrecuenciaSuscripcion.choices, required=False)
    maximo_sedes = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    maximo_empleados = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    maximo_canchas = serializers.IntegerField(min_value=0, allow_null=True, required=False)
    activo = serializers.BooleanField(required=False)

    def validate(self, datos):
        plan = self.context.get("plan")
        for campo in ("nombre", "precio", "moneda", "frecuencia"):
            if not self.partial and campo not in datos and not plan:
                raise serializers.ValidationError({campo: "Este campo es obligatorio."})
        nombre = datos.get("nombre", getattr(plan, "nombre", None))
        if nombre:
            existentes = PlanSuscripcion.objects.annotate(
                nombre_normalizado=Lower("nombre")
            ).filter(nombre_normalizado=nombre.lower())
            if plan:
                existentes = existentes.exclude(pk=plan.pk)
            if existentes.exists():
                raise serializers.ValidationError({"nombre": "Ya existe un plan con ese nombre."})
        return datos


class SolicitudSuscripcionEntrada(EntradaEstricta):
    plan_id = serializers.IntegerField(min_value=1)
    medio_declarado = serializers.CharField(max_length=40, required=False, allow_blank=True)
    referencia_declarada = serializers.CharField(max_length=120, required=False, allow_blank=True)
    nota = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ResolverSolicitudEntrada(EntradaEstricta):
    aprobar = serializers.BooleanField()
    importe_verificado = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    referencia_verificada = serializers.CharField(max_length=120, required=False, allow_blank=True)
    medio_verificado = serializers.CharField(max_length=40, required=False, allow_blank=True)
    fecha_inicio = serializers.DateField(required=False)

    def validate(self, datos):
        if datos.get("aprobar") and "importe_verificado" not in datos:
            raise serializers.ValidationError({
                "importe_verificado": "Confirma el importe recibido para aprobar la solicitud."
            })
        return datos


class GraciaEntrada(EntradaEstricta):
    dias_gracia = serializers.IntegerField(min_value=0)
