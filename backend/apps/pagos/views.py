from typing import ClassVar

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.pagos.serializers import (
    AprobarPagoEntrada,
    DeclararComprobanteEntrada,
    FiltrosPagosEntrada,
    MetodoPagoEntrada,
    RechazarPagoEntrada,
    SolicitudPagoEntrada,
)
from apps.pagos.services.metodos import guardar_metodo, listar_metodos_personal
from apps.pagos.services.pagos import (
    aprobar_pago,
    consultar_pago_propietario,
    crear_solicitud_pago,
    declarar_comprobante,
    listar_pagos_administrables,
    pago_administrable,
    rechazar_pago,
)
from apps.pagos.services.representacion import (
    datos_metodo,
    datos_pago,
    datos_pago_administrativo,
)


def _exigir_pagos_habilitados() -> None:
    from django.conf import settings

    if not settings.PAGOS_RESERVA_HABILITADOS:
        raise PermissionDenied(
            "Los pagos de reserva están deshabilitados hasta aprobar los plazos y condiciones comerciales."
        )


class MediosPagoSedeView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, sede_id: int) -> Response:
        metodos = listar_metodos_personal(request.user, sede_id)
        return Response([datos_metodo(item, request) for item in metodos])

    def post(self, request: Request, sede_id: int) -> Response:
        entrada = MetodoPagoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        metodo = guardar_metodo(request.user, sede_id, entrada.validated_data.copy())
        return Response(datos_metodo(metodo, request), status=status.HTTP_200_OK)


class PagoReservaPropiaView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, codigo: str) -> Response:
        resultado = consultar_pago_propietario(request.user, codigo, request)
        if resultado is None:
            return Response({"detail": "No se encontró esa reserva en tu cuenta."}, status=404)
        from django.conf import settings

        resultado["habilitado"] = settings.PAGOS_RESERVA_HABILITADOS
        return Response(resultado)


class SolicitudPagoPropiaView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def post(self, request: Request, codigo: str) -> Response:
        _exigir_pagos_habilitados()
        entrada = SolicitudPagoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        pago = crear_solicitud_pago(
            request.user, codigo, datos["tipo"], datos["metodo_id"], datos["clave_idempotencia"],
        )
        if pago is None:
            return Response({"detail": "La retención venció y el horario fue liberado."}, status=409)
        return Response(datos_pago(pago, request), status=status.HTTP_201_CREATED)


class DeclararComprobantePropioView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def post(self, request: Request, codigo: str, pago_id: int) -> Response:
        _exigir_pagos_habilitados()
        entrada = DeclararComprobanteEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        pago, tardio = declarar_comprobante(
            request.user, codigo, pago_id,
            entrada.validated_data.get("referencia", ""),
            entrada.validated_data.get("observacion", ""),
        )
        if pago is None:
            return Response({"detail": "No se encontró ese pago en tu cuenta."}, status=404)
        return Response(
            datos_pago(pago, request), status=status.HTTP_409_CONFLICT if tardio else status.HTTP_200_OK,
        )


class PagosAdministracionView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        entrada = FiltrosPagosEntrada(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        pagos = listar_pagos_administrables(request.user, entrada.validated_data)
        return Response({"count": len(pagos), "results": [datos_pago_administrativo(item, request) for item in pagos]})


class PagoAdministracionDetalleView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, pago_id: int) -> Response:
        pago = pago_administrable(request.user, pago_id)
        return Response(datos_pago_administrativo(pago, request))


class RevisarPagoAdministracionView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def post(self, request: Request, pago_id: int, accion: str) -> Response:
        _exigir_pagos_habilitados()
        pago = pago_administrable(request.user, pago_id)
        if pago.reserva.jugador_id == request.user.pk:
            raise PermissionDenied("No puedes revisar un pago de una reserva propia.")
        if accion == "aprobar":
            entrada = AprobarPagoEntrada(data=request.data)
            entrada.is_valid(raise_exception=True)
            resultado, vigente = aprobar_pago(
                request.user, pago_id,
                entrada.validated_data.get("importe_verificado"),
                entrada.validated_data.get("motivo", ""),
            )
            return Response(
                datos_pago_administrativo(resultado, request),
                status=status.HTTP_200_OK if vigente else status.HTTP_409_CONFLICT,
            )
        if accion != "rechazar":
            raise PermissionDenied("Acción de revisión no permitida.")
        entrada = RechazarPagoEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        resultado, vigente = rechazar_pago(request.user, pago_id, entrada.validated_data["motivo"])
        return Response(
            datos_pago_administrativo(resultado, request),
            status=status.HTTP_200_OK if vigente else status.HTTP_409_CONFLICT,
        )
