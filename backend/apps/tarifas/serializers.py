from decimal import Decimal

from rest_framework import serializers

from apps.empresas.serializers import EntradaEstricta
from apps.tarifas.models import ReglaTarifa, TipoTarifa


class ReglaTarifaEntrada(EntradaEstricta):
    tipo = serializers.ChoiceField(choices=TipoTarifa.choices)
    nombre = serializers.CharField(max_length=120, required=False, allow_blank=True)
    dias_semana = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        max_length=7, required=False, default=list,
    )
    fecha_aplicable_desde = serializers.DateField(required=False, allow_null=True)
    fecha_aplicable_hasta = serializers.DateField(required=False, allow_null=True)
    hora_inicio = serializers.TimeField(
        required=False, allow_null=True, format="%H:%M", input_formats=["%H:%M"],
    )
    hora_fin = serializers.TimeField(
        required=False, allow_null=True, format="%H:%M", input_formats=["%H:%M"],
    )
    todo_el_dia = serializers.BooleanField(required=False, default=False)
    vigente_desde = serializers.DateField()
    vigente_hasta = serializers.DateField(required=False, allow_null=True)
    precio_hora = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01"),
    )
    moneda = serializers.ChoiceField(choices=[("PEN", "PEN")], default="PEN")

    def validate_nombre(self, value: str) -> str:
        return value.strip()

    def validate(self, datos: dict) -> dict:
        instancia = self.instance
        campos = (
            "tipo", "dias_semana", "fecha_aplicable_desde", "fecha_aplicable_hasta",
            "hora_inicio", "hora_fin", "todo_el_dia", "vigente_desde", "vigente_hasta",
        )
        completos = {
            campo: datos.get(campo, getattr(instancia, campo, None)) for campo in campos
        }
        if completos["vigente_desde"] is None:
            raise serializers.ValidationError({"vigente_desde": "Indica desde cuándo rige el precio."})
        if completos["vigente_hasta"] and completos["vigente_hasta"] < completos["vigente_desde"]:
            raise serializers.ValidationError({
                "vigente_hasta": "La fecha final debe ser igual o posterior al inicio de vigencia."
            })

        tipo = completos["tipo"]
        dias = completos["dias_semana"] or []
        if len(set(dias)) != len(dias):
            raise serializers.ValidationError({"dias_semana": "No repitas días de la semana."})
        fecha_inicio = completos["fecha_aplicable_desde"]
        fecha_fin = completos["fecha_aplicable_hasta"]
        if tipo in (TipoTarifa.DIURNA, TipoTarifa.NOCTURNA):
            if not dias:
                raise serializers.ValidationError({"dias_semana": "Elige al menos un día."})
            if fecha_inicio or fecha_fin:
                raise serializers.ValidationError({
                    "fecha_aplicable_desde": "Las tarifas diurnas y nocturnas se configuran por día de semana."
                })
        elif tipo == TipoTarifa.FIN_SEMANA:
            if dias or fecha_inicio or fecha_fin:
                raise serializers.ValidationError({
                    "tipo": "La tarifa de fin de semana se aplica a sábado y domingo."
                })
        else:
            if dias:
                raise serializers.ValidationError({"dias_semana": "Las fechas especiales no usan días semanales."})
            if not fecha_inicio or not fecha_fin:
                raise serializers.ValidationError({
                    "fecha_aplicable_desde": "Indica el inicio y fin de las fechas a las que aplica."
                })
            if fecha_fin < fecha_inicio:
                raise serializers.ValidationError({
                    "fecha_aplicable_hasta": "La fecha final debe ser igual o posterior al inicio."
                })
            vigencia_fin = completos["vigente_hasta"] or fecha_fin
            if max(completos["vigente_desde"], fecha_inicio) > min(vigencia_fin, fecha_fin):
                raise serializers.ValidationError({
                    "vigente_desde": "La vigencia debe coincidir con alguna fecha de aplicación."
                })

        hora_inicio = completos["hora_inicio"]
        hora_fin = completos["hora_fin"]
        if completos["todo_el_dia"]:
            if hora_inicio is not None or hora_fin is not None:
                raise serializers.ValidationError({
                    "todo_el_dia": "Quita las horas para aplicar la tarifa todo el día."
                })
        elif hora_inicio is None or hora_fin is None:
            raise serializers.ValidationError({
                "hora_inicio": "Indica el inicio y fin del horario o selecciona todo el día."
            })
        elif hora_inicio == hora_fin:
            raise serializers.ValidationError({
                "hora_fin": "El inicio y fin deben ser distintos; para todo el día usa esa opción."
            })
        return datos


class EstadoReglaTarifaEntrada(EntradaEstricta):
    activa = serializers.BooleanField()
    confirmar = serializers.BooleanField()


class CalcularPrecioEntrada(EntradaEstricta):
    fecha = serializers.DateField()
    hora_inicio = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])
    duracion_horas = serializers.IntegerField(min_value=1, max_value=24)


def datos_regla_tarifa(regla: ReglaTarifa) -> dict:
    return {
        "id": regla.pk,
        "cancha_id": regla.cancha_id,
        "tipo": regla.tipo,
        "nombre": regla.nombre,
        "dias_semana": regla.dias_semana,
        "fecha_aplicable_desde": (
            regla.fecha_aplicable_desde.isoformat() if regla.fecha_aplicable_desde else None
        ),
        "fecha_aplicable_hasta": (
            regla.fecha_aplicable_hasta.isoformat() if regla.fecha_aplicable_hasta else None
        ),
        "hora_inicio": regla.hora_inicio.strftime("%H:%M") if regla.hora_inicio else None,
        "hora_fin": regla.hora_fin.strftime("%H:%M") if regla.hora_fin else None,
        "todo_el_dia": regla.todo_el_dia,
        "vigente_desde": regla.vigente_desde.isoformat(),
        "vigente_hasta": regla.vigente_hasta.isoformat() if regla.vigente_hasta else None,
        "precio_hora": f"{regla.precio_hora:.2f}",
        "moneda": regla.moneda,
        "activa": regla.activa,
        "creada_en": regla.creada_en.isoformat(),
        "actualizada_en": regla.actualizada_en.isoformat(),
    }
