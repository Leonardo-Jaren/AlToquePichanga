from typing import ClassVar

from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.empresas.serializers import EntradaEstricta
from apps.reservas.services.asistencia import consultar_ingreso, registrar_ingreso


class EntradaIngreso(EntradaEstricta):
    tipo = serializers.ChoiceField(choices=["qr", "codigo"])
    valor = serializers.CharField(max_length=256, trim_whitespace=True)


class LimiteIngreso(UserRateThrottle):
    scope = "ingreso_reserva"
    rate = "30/min"


class IngresoReservaView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]
    throttle_classes: ClassVar[list] = [LimiteIngreso]

    def post(self, request: Request, accion: str) -> Response:
        entrada = EntradaIngreso(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        if accion == "consultar":
            return Response(consultar_ingreso(request.user, datos["valor"], datos["tipo"]))
        if accion == "registrar":
            resultado, creada = registrar_ingreso(request.user, datos["valor"], datos["tipo"])
            return Response(resultado, status=status.HTTP_201_CREATED if creada else status.HTTP_409_CONFLICT)
        return Response({"detail": "Acción no permitida."}, status=status.HTTP_404_NOT_FOUND)
