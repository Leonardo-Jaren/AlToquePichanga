from decimal import Decimal

from rest_framework import serializers

from apps.empresas.serializers import EntradaEstricta
from apps.pagos.models import EstadoPagoReserva, TipoMetodoPago, TipoPagoReserva
from shared.archivos import validar_imagen_segura


class MetodoPagoEntrada(EntradaEstricta):
    tipo = serializers.ChoiceField(choices=TipoMetodoPago.choices)
    titular = serializers.CharField(max_length=160)
    numero_cuenta = serializers.CharField(max_length=40, required=False, allow_blank=True)
    banco = serializers.CharField(max_length=100, required=False, allow_blank=True)
    cci = serializers.CharField(max_length=24, required=False, allow_blank=True)
    imagen_qr = serializers.FileField(required=False, allow_empty_file=False)
    instrucciones = serializers.CharField(max_length=240, required=False, allow_blank=True)
    activo = serializers.BooleanField(required=False, default=True)

    def validate_titular(self, value: str) -> str:
        if not value.strip():
            raise serializers.ValidationError("Indica el titular que recibirá el pago.")
        return value.strip()

    def validate_imagen_qr(self, value):
        validar_imagen_segura(value)
        return value

    def validate(self, datos: dict) -> dict:
        tipo = datos["tipo"]
        numero = datos.get("numero_cuenta", "").strip()
        banco = datos.get("banco", "").strip()
        cci = datos.get("cci", "").strip()
        if tipo in {TipoMetodoPago.YAPE, TipoMetodoPago.PLIN} and not numero:
            raise serializers.ValidationError({"numero_cuenta": "Indica el número de celular asociado."})
        if tipo == TipoMetodoPago.TRANSFERENCIA and not (numero or cci):
            raise serializers.ValidationError({"numero_cuenta": "Indica la cuenta o el CCI."})
        if tipo == TipoMetodoPago.TRANSFERENCIA and not banco:
            raise serializers.ValidationError({"banco": "Indica el banco de la cuenta."})
        return datos


class SolicitudPagoEntrada(EntradaEstricta):
    tipo = serializers.ChoiceField(choices=TipoPagoReserva.choices)
    metodo_id = serializers.IntegerField(min_value=1)
    clave_idempotencia = serializers.UUIDField()


class DeclararComprobanteEntrada(EntradaEstricta):
    referencia = serializers.CharField(max_length=100, required=False, allow_blank=True)
    observacion = serializers.CharField(max_length=240, required=False, allow_blank=True)


class AprobarPagoEntrada(EntradaEstricta):
    importe_verificado = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01"), required=False
    )
    motivo = serializers.CharField(max_length=240, required=False, allow_blank=True)


class RechazarPagoEntrada(EntradaEstricta):
    motivo = serializers.CharField(max_length=240, min_length=6)


class FiltrosPagosEntrada(EntradaEstricta):
    sede = serializers.IntegerField(min_value=1, required=False)
    estado = serializers.ChoiceField(choices=EstadoPagoReserva.choices, required=False)
    desde = serializers.DateField(format="%Y-%m-%d", required=False)
    hasta = serializers.DateField(format="%Y-%m-%d", required=False)
    q = serializers.CharField(max_length=80, required=False, allow_blank=True)

    def validate(self, datos: dict) -> dict:
        if datos.get("desde") and datos.get("hasta") and datos["hasta"] < datos["desde"]:
            raise serializers.ValidationError({"hasta": "La fecha final debe ser igual o posterior."})
        return datos


class PagoReservaLectura(serializers.Serializer):
    id = serializers.IntegerField()
    codigo_reserva = serializers.CharField()
    estado = serializers.ChoiceField(choices=EstadoPagoReserva.choices)
    tipo = serializers.ChoiceField(choices=TipoPagoReserva.choices)
    importe_solicitado = serializers.DecimalField(max_digits=10, decimal_places=2)
    importe_verificado = serializers.DecimalField(max_digits=10, decimal_places=2)
    referencia = serializers.CharField()
    observacion_jugador = serializers.CharField()
    motivo_revision = serializers.CharField()
    creado_en = serializers.DateTimeField()
    declarado_en = serializers.DateTimeField(allow_null=True)
    revisado_en = serializers.DateTimeField(allow_null=True)
    requiere_conciliacion = serializers.BooleanField()
    metodo = serializers.DictField()
    historial = serializers.ListField(child=serializers.DictField())


class ReservaPagoLectura(serializers.Serializer):
    codigo = serializers.CharField()
    cancha = serializers.CharField()
    sede = serializers.CharField()
    inicio = serializers.DateTimeField()
    fin = serializers.DateTimeField()
    estado_reserva = serializers.CharField()
    moneda = serializers.CharField()
    importe_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    adelanto_minimo = serializers.DecimalField(max_digits=10, decimal_places=2)
    importe_pagado = serializers.DecimalField(max_digits=10, decimal_places=2)
    saldo_pendiente = serializers.DecimalField(max_digits=10, decimal_places=2)
    vence_en = serializers.DateTimeField(allow_null=True)
    whatsapp_url = serializers.URLField(allow_null=True)
    metodos = serializers.ListField(child=serializers.DictField())
    pagos = PagoReservaLectura(many=True)


class PagoAdminLectura(PagoReservaLectura):
    jugador = serializers.DictField()
    empresa = serializers.CharField()
    cancha = serializers.CharField()
    sede = serializers.CharField()

