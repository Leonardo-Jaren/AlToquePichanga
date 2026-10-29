from typing import ClassVar

from rest_framework import serializers

from apps.empresas.serializers import EntradaEstricta
from apps.reservas.models import EstadoReserva, Reserva


class SolicitarReservaEntrada(EntradaEstricta):
    cancha_id = serializers.IntegerField(min_value=1)
    fecha = serializers.DateField(format="%Y-%m-%d")
    hora_inicio = serializers.TimeField(format="%H:%M", input_formats=["%H:%M"])
    duracion_horas = serializers.IntegerField(min_value=1, max_value=24)
    clave_idempotencia = serializers.UUIDField()


class FiltrosReservasEntrada(EntradaEstricta):
    desde = serializers.DateField(format="%Y-%m-%d", required=False)
    hasta = serializers.DateField(format="%Y-%m-%d", required=False)
    estado = serializers.ChoiceField(choices=EstadoReserva.choices, required=False)
    cancha = serializers.IntegerField(min_value=1, required=False)
    sede = serializers.IntegerField(min_value=1, required=False)
    empresa = serializers.IntegerField(min_value=1, required=False)
    q = serializers.CharField(max_length=80, trim_whitespace=True, required=False, allow_blank=True)

    def validate(self, datos):
        if datos.get("desde") and datos.get("hasta") and datos["hasta"] < datos["desde"]:
            raise serializers.ValidationError({"hasta": "La fecha final debe ser igual o posterior."})
        return datos


class ReservaLecturaSerializer(serializers.ModelSerializer):
    cancha_nombre = serializers.CharField(source="cancha.nombre", read_only=True)
    sede_nombre = serializers.CharField(source="cancha.sede.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="cancha.sede.empresa.nombre_visible", read_only=True)
    jugador = serializers.SerializerMethodField()

    class Meta:
        model = Reserva
        fields: ClassVar[list[str]] = [
            "codigo", "cancha_id", "cancha_nombre", "sede_nombre", "empresa_nombre",
            "inicio", "fin", "duracion_horas", "importe_total", "adelanto_minimo",
            "moneda", "estado", "retencion_vence_en", "cotizacion_aplicada",
            "creada_en", "jugador",
        ]
        read_only_fields: ClassVar[list[str]] = fields

    def get_jugador(self, reserva: Reserva) -> dict | None:
        if not self.context.get("administrativa"):
            return None
        return {
            "id": reserva.jugador_id,
            "nombre": reserva.jugador.get_full_name() or reserva.jugador.username,
            "correo": reserva.jugador.email,
        }
