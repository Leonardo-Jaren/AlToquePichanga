from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.canchas.models import EstadoCancha
from apps.canchas.serializers import (
    CanchaEntrada,
    EstadoCanchaEntrada,
    ImagenCanchaEntrada,
    datos_cancha,
)
from apps.canchas.services.canchas import (
    actualizar_cancha,
    cambiar_estado_cancha,
    cancha_editable,
    consultar_cancha,
    crear_cancha,
    listar_canchas,
)
from apps.canchas.services.imagenes import agregar_imagen, retirar_imagen
from apps.empresas.serializers import EntradaEstricta


class FiltrosCanchaEntrada(EntradaEstricta):
    sede = serializers.IntegerField(min_value=1, required=False)
    modalidad = serializers.IntegerField(min_value=1, max_value=32767, required=False)
    estado = serializers.ChoiceField(choices=EstadoCancha.choices, required=False)
    buscar = serializers.CharField(max_length=100, required=False, allow_blank=True)
    page = serializers.IntegerField(min_value=1, required=False)
    page_size = serializers.IntegerField(min_value=1, max_value=100, required=False)


class PaginacionCanchas(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ConfirmarRetiroEntrada(EntradaEstricta):
    confirmar = serializers.BooleanField()


class CanchasView(APIView):
    def get(self, request: Request) -> Response:
        filtros = FiltrosCanchaEntrada(data=request.query_params)
        filtros.is_valid(raise_exception=True)
        queryset = listar_canchas(request.user, filtros.validated_data)
        paginador = PaginacionCanchas()
        pagina = paginador.paginate_queryset(queryset, request, view=self)
        return paginador.get_paginated_response([datos_cancha(cancha) for cancha in pagina])

    def post(self, request: Request) -> Response:
        serializer = CanchaEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(crear_cancha(request.user, serializer.validated_data), status=201)


class CanchaView(APIView):
    def get(self, request: Request, cancha_id: int) -> Response:
        return Response(consultar_cancha(request.user, cancha_id))

    def patch(self, request: Request, cancha_id: int) -> Response:
        modelo = cancha_editable(request.user, cancha_id)
        serializer = CanchaEntrada(
            data=request.data, partial=True, context={"cancha": modelo}
        )
        serializer.is_valid(raise_exception=True)
        return Response(actualizar_cancha(request.user, cancha_id, serializer.validated_data))


class EstadoCanchaView(APIView):
    def post(self, request: Request, cancha_id: int) -> Response:
        serializer = EstadoCanchaEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmar"]:
            raise serializers.ValidationError({"confirmar": "Confirma el cambio de estado."})
        return Response(cambiar_estado_cancha(
            request.user, cancha_id, serializer.validated_data["estado"]
        ))


class ImagenesCanchaView(APIView):
    def post(self, request: Request, cancha_id: int) -> Response:
        serializer = ImagenCanchaEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(agregar_imagen(request.user, cancha_id, serializer.validated_data), status=201)


class RetirarImagenCanchaView(APIView):
    def post(self, request: Request, cancha_id: int, imagen_id: int) -> Response:
        serializer = ConfirmarRetiroEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmar"]:
            raise serializers.ValidationError({"confirmar": "Confirma el retiro de la imagen."})
        return Response(retirar_imagen(request.user, cancha_id, imagen_id))
