from datetime import datetime
from typing import ClassVar

from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.canchas.services.publicacion import (
    cancha_publicada,
    canchas_publicadas,
    datos_cancha_publica,
)
from apps.horarios.serializers import DisponibilidadEntrada
from apps.reservas.services.disponibilidad import (
    consultar_disponibilidad_reservable,
    horario_reservado,
)
from apps.reservas.services.reservas import HorarioNoDisponible
from apps.tarifas.serializers import CalcularPrecioEntrada
from apps.tarifas.services.disponibilidad import (
    previsualizar_precio_para_cancha,
)


class VistaPublica(APIView):
    authentication_classes: ClassVar[list] = []
    permission_classes: ClassVar[list] = [AllowAny]


class CanchasPublicasView(VistaPublica):
    def get(self, request: Request) -> Response:
        return Response([datos_cancha_publica(cancha) for cancha in canchas_publicadas()])


class CanchaPublicaView(VistaPublica):
    def get(self, request: Request, cancha_id: int) -> Response:
        return Response(datos_cancha_publica(cancha_publicada(cancha_id)))


class DisponibilidadCanchaPublicaView(VistaPublica):
    def get(self, request: Request, cancha_id: int) -> Response:
        filtros = DisponibilidadEntrada(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        cancha = cancha_publicada(cancha_id)
        return Response(consultar_disponibilidad_reservable(
            cancha, filtros.validated_data["desde"], filtros.validated_data["hasta"],
            publica=True,
        ))


class CotizacionCanchaPublicaView(VistaPublica):
    def post(self, request: Request, cancha_id: int) -> Response:
        entrada = CalcularPrecioEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        cancha = cancha_publicada(cancha_id)
        inicio = datetime.combine(datos["fecha"], datos["hora_inicio"])
        if horario_reservado(cancha.pk, inicio, datos["duracion_horas"]):
            raise HorarioNoDisponible()
        try:
            cotizacion = previsualizar_precio_para_cancha(
                cancha, datos["fecha"], datos["hora_inicio"], datos["duracion_horas"]
            )
        except ValidationError as error:
            raise ValidationError({
                "cotizacion": "Selecciona bloques operativos consecutivos con tarifa configurada.",
            }) from error
        return Response(cotizacion)
