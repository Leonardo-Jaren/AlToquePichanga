from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.horarios.serializers import (
    ConfirmarAnulacionEntrada,
    DisponibilidadEntrada,
    ExcepcionHorarioEntrada,
    FiltrosExcepcionEntrada,
    HorarioCanchaEntrada,
    HorarioSedeEntrada,
)
from apps.horarios.services.disponibilidad import consultar_disponibilidad_operativa
from apps.horarios.services.excepciones import (
    anular_excepcion,
    crear_excepcion,
    listar_excepciones,
)
from apps.horarios.services.horarios import (
    consultar_horario_cancha,
    consultar_horario_sede,
    guardar_horario_cancha,
    guardar_horario_sede,
)


class HorarioSedeView(APIView):
    def get(self, request: Request, sede_id: int) -> Response:
        return Response(consultar_horario_sede(request.user, sede_id))

    def put(self, request: Request, sede_id: int) -> Response:
        entrada = HorarioSedeEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        return Response(guardar_horario_sede(
            request.user, sede_id, entrada.validated_data["intervalos"]
        ))


class HorarioCanchaView(APIView):
    def get(self, request: Request, cancha_id: int) -> Response:
        return Response(consultar_horario_cancha(request.user, cancha_id))

    def put(self, request: Request, cancha_id: int) -> Response:
        entrada = HorarioCanchaEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        return Response(guardar_horario_cancha(
            request.user,
            cancha_id,
            entrada.validated_data["hereda_horario_sede"],
            entrada.validated_data.get("dias_heredados", []),
            entrada.validated_data["intervalos"],
        ))


class ExcepcionesHorarioView(APIView):
    def get(self, request: Request) -> Response:
        filtros = FiltrosExcepcionEntrada(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        excepciones = listar_excepciones(request.user, filtros.validated_data)
        return Response({"count": len(excepciones), "results": excepciones})

    def post(self, request: Request) -> Response:
        entrada = ExcepcionHorarioEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        return Response(crear_excepcion(request.user, entrada.validated_data), status=201)


class AnularExcepcionHorarioView(APIView):
    def post(self, request: Request, excepcion_id: int) -> Response:
        entrada = ConfirmarAnulacionEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        if not entrada.validated_data["confirmar"]:
            raise serializers.ValidationError({"confirmar": "Confirma la anulación."})
        return Response(anular_excepcion(request.user, excepcion_id))


class DisponibilidadOperativaView(APIView):
    def get(self, request: Request, cancha_id: int) -> Response:
        filtros = DisponibilidadEntrada(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        return Response(consultar_disponibilidad_operativa(
            request.user, cancha_id, filtros.validated_data["desde"],
            filtros.validated_data["hasta"],
        ))
