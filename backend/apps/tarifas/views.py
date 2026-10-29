from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tarifas.repositories.tarifas import cancha_tarifaria, reglas_de_cancha
from apps.tarifas.serializers import (
    CalcularPrecioEntrada,
    EstadoReglaTarifaEntrada,
    ReglaTarifaEntrada,
)
from apps.tarifas.services.disponibilidad import previsualizar_precio
from apps.tarifas.services.gestion import (
    actualizar_tarifa,
    cambiar_estado_tarifa,
    crear_tarifa,
    listar_tarifas,
)


class TarifasCanchaView(APIView):
    def get(self, request: Request, cancha_id: int) -> Response:
        return Response(listar_tarifas(request.user, cancha_id))

    def post(self, request: Request, cancha_id: int) -> Response:
        entrada = ReglaTarifaEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        return Response(crear_tarifa(
            request.user, cancha_id, entrada.validated_data
        ), status=201)


class ReglaTarifaView(APIView):
    def patch(self, request: Request, cancha_id: int, tarifa_id: int) -> Response:
        cancha = cancha_tarifaria(request.user, cancha_id)
        regla = get_object_or_404(reglas_de_cancha(cancha), pk=tarifa_id)
        entrada = ReglaTarifaEntrada(instance=regla, data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        return Response(actualizar_tarifa(
            request.user, cancha_id, tarifa_id, entrada.validated_data
        ))


class EstadoReglaTarifaView(APIView):
    def post(self, request: Request, cancha_id: int, tarifa_id: int) -> Response:
        entrada = EstadoReglaTarifaEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        if not entrada.validated_data["confirmar"]:
            raise serializers.ValidationError({"confirmar": "Confirma el cambio de estado."})
        return Response(cambiar_estado_tarifa(
            request.user, cancha_id, tarifa_id, entrada.validated_data["activa"]
        ))


class CalcularPrecioView(APIView):
    def post(self, request: Request, cancha_id: int) -> Response:
        entrada = CalcularPrecioEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        return Response(previsualizar_precio(
            request.user, cancha_id, datos["fecha"], datos["hora_inicio"],
            datos["duracion_horas"],
        ))
