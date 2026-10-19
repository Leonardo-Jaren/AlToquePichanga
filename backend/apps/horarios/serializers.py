from datetime import datetime

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from apps.empresas.serializers import EntradaEstricta
from apps.horarios.models import TipoExcepcionHorario


class IntervaloHorarioEntrada(EntradaEstricta):
    dia_semana = serializers.IntegerField(min_value=0, max_value=6)
    hora_apertura = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])
    hora_cierre = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])

    def validate(self, datos):
        if datos["hora_apertura"] == datos["hora_cierre"]:
            raise serializers.ValidationError({
                "hora_cierre": "La apertura y el cierre deben ser distintos."
            })
        return datos


class HorarioSedeEntrada(EntradaEstricta):
    intervalos = IntervaloHorarioEntrada(many=True, max_length=100)


class HorarioCanchaEntrada(EntradaEstricta):
    hereda_horario_sede = serializers.BooleanField()
    dias_heredados = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
        max_length=7,
    )
    intervalos = IntervaloHorarioEntrada(many=True, max_length=100)


class ExcepcionHorarioEntrada(EntradaEstricta):
    sede_id = serializers.IntegerField(min_value=1)
    cancha_id = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    tipo = serializers.ChoiceField(choices=TipoExcepcionHorario.choices)
    fecha_inicio = serializers.DateTimeField()
    fecha_fin = serializers.DateTimeField()
    motivo = serializers.CharField(max_length=300, trim_whitespace=True)

    def _fecha_entrada_aware(self, nombre: str) -> bool:
        valor = self.initial_data.get(nombre)
        if isinstance(valor, datetime):
            return timezone.is_aware(valor)
        if not isinstance(valor, str):
            return False
        fecha = parse_datetime(valor)
        return bool(fecha and timezone.is_aware(fecha))

    def validate(self, datos):
        errores = {}
        for nombre in ("fecha_inicio", "fecha_fin"):
            if not self._fecha_entrada_aware(nombre):
                errores[nombre] = "Usa fecha y hora ISO-8601 con offset horario explícito."
        if errores:
            raise serializers.ValidationError(errores)
        if datos["fecha_fin"] <= datos["fecha_inicio"]:
            raise serializers.ValidationError({
                "fecha_fin": "La fecha final debe ser posterior a la inicial."
            })
        if not datos["motivo"].strip():
            raise serializers.ValidationError({"motivo": "Ingresa el motivo de la excepción."})
        return datos


class FiltrosExcepcionEntrada(EntradaEstricta):
    sede = serializers.IntegerField(min_value=1, required=False)
    cancha = serializers.IntegerField(min_value=1, required=False)
    desde = serializers.DateField(format="%Y-%m-%d", required=False)
    hasta = serializers.DateField(format="%Y-%m-%d", required=False)


class DisponibilidadEntrada(EntradaEstricta):
    desde = serializers.DateField(format="%Y-%m-%d")
    hasta = serializers.DateField(format="%Y-%m-%d")

    def validate(self, datos):
        desde, hasta = datos["desde"], datos["hasta"]
        if hasta < desde:
            raise serializers.ValidationError({"hasta": "La fecha final debe ser posterior o igual."})
        max_dias = getattr(settings, "MAX_DIAS_CONSULTA_DISPONIBILIDAD", 31)
        if (hasta - desde).days + 1 > max_dias:
            raise serializers.ValidationError({
                "hasta": f"El rango máximo de consulta es de {max_dias} días calendario."
            })
        return datos


class ConfirmarAnulacionEntrada(EntradaEstricta):
    confirmar = serializers.BooleanField()
