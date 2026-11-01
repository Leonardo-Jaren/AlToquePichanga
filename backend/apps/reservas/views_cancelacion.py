from typing import ClassVar

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empresas.serializers import EntradaEstricta
from apps.reservas.serializers import ReservaLecturaSerializer
from apps.reservas.services.cancelacion import cancelar_reserva


class EntradaCancelacion(EntradaEstricta):
    motivo = serializers.CharField(max_length=240, trim_whitespace=True)


class CancelarReservaView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]
    administrativa = False

    def post(self, request: Request, codigo: str) -> Response:
        entrada = EntradaCancelacion(data=request.data)
        entrada.is_valid(raise_exception=True)
        reserva, revision = cancelar_reserva(
            request.user, codigo, entrada.validated_data["motivo"], administrativa=self.administrativa,
        )
        return Response({**ReservaLecturaSerializer(reserva).data, "requiere_revision": revision})


class CancelarReservaAdministrativaView(CancelarReservaView):
    administrativa = True
