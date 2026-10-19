from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empresas.serializers import EntradaEstricta
from apps.suscripciones.models import EstadoSuscripcion
from apps.suscripciones.serializers import (
    GraciaEntrada,
    PlanEntrada,
    ResolverSolicitudEntrada,
    SolicitudSuscripcionEntrada,
)
from apps.suscripciones.services import suscripciones


class PaginacionSolicitudes(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PlanesView(APIView):
    def get(self, request):
        if request.user.is_superuser:
            datos = suscripciones.planes_plataforma(request.user)
        else:
            datos = suscripciones.planes_disponibles(request.user)
        return Response(datos)

    def post(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied("Solo el superadministrador puede gestionar planes.")
        serializer = PlanEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            suscripciones.guardar_plan(request.user, None, serializer.validated_data),
            status=201,
        )


class PlanView(APIView):
    def patch(self, request, plan_id: int):
        if not request.user.is_superuser:
            raise PermissionDenied("Solo el superadministrador puede gestionar planes.")
        plan = suscripciones.modelo_plan_plataforma(request.user, plan_id)
        serializer = PlanEntrada(data=request.data, partial=True, context={"plan": plan})
        serializer.is_valid(raise_exception=True)
        return Response(suscripciones.guardar_plan(
            request.user, plan_id, serializer.validated_data
        ))


class SuscripcionEmpresaView(APIView):
    def get(self, request, empresa_id: int):
        return Response(suscripciones.resumen_empresa(request.user, empresa_id))

    def post(self, request, empresa_id: int):
        serializer = SolicitudSuscripcionEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(suscripciones.solicitar_suscripcion(
            request.user, empresa_id, serializer.validated_data
        ), status=201)


class SolicitudesSuscripcionView(APIView):
    def get(self, request):
        estado = request.query_params.get("estado", "").strip()
        datos = suscripciones.listar_solicitudes_plataforma(request.user, estado)
        paginador = PaginacionSolicitudes()
        filas = paginador.paginate_queryset(datos, request, view=self)
        return paginador.get_paginated_response(filas)


class ResolverSolicitudView(APIView):
    def post(self, request, solicitud_id: int):
        serializer = ResolverSolicitudEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(suscripciones.resolver_solicitud(
            request.user, solicitud_id, serializer.validated_data
        ))


class EstadoSuscripcionEntrada(EntradaEstricta):
    estado = serializers.ChoiceField(choices=EstadoSuscripcion.choices)


class EstadoSuscripcionView(APIView):
    def post(self, request, empresa_id: int):
        serializer = EstadoSuscripcionEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(suscripciones.cambiar_estado(
            request.user, empresa_id, serializer.validated_data["estado"]
        ))


class ConfiguracionSuscripcionView(APIView):
    def get(self, request):
        return Response({"dias_gracia": suscripciones.consultar_dias_gracia(request.user)})

    def put(self, request):
        serializer = GraciaEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(suscripciones.configurar_dias_gracia(
            request.user, serializer.validated_data["dias_gracia"]
        ))
