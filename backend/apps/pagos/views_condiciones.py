from typing import ClassVar

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empresas.serializers import EntradaEstricta
from apps.pagos.services.condiciones import (
    consultar_condicion,
    datos_condicion,
    publicar_condicion,
)


class CondicionEntrada(EntradaEstricta):
    texto = serializers.CharField(max_length=6000, trim_whitespace=True)


class CondicionesSedeView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, sede_id: int) -> Response:
        return Response(consultar_condicion(request.user, sede_id))

    def put(self, request: Request, sede_id: int) -> Response:
        entrada = CondicionEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        return Response(datos_condicion(publicar_condicion(request.user, sede_id, entrada.validated_data["texto"])))
