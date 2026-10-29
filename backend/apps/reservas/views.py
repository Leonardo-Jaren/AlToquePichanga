from typing import ClassVar

from django.db.models import Q, QuerySet
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.canchas.repositories.canchas import canchas_visibles
from apps.empresas.models import MembresiaEmpresa, RegistroAuditoria, RolEmpresa
from apps.horarios.serializers import DisponibilidadEntrada
from apps.reservas.models import Reserva
from apps.reservas.serializers import (
    FiltrosReservasEntrada,
    ReservaLecturaSerializer,
    SolicitarReservaEntrada,
)
from apps.reservas.services.disponibilidad import consultar_disponibilidad_reservable
from apps.reservas.services.reservas import cancelar_retencion, crear_retencion


class PaginacionReservas(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


def _exigir_personal(usuario) -> None:
    if usuario.is_superuser:
        return
    autorizado = MembresiaEmpresa.objects.filter(
        usuario=usuario,
        activa=True,
        empresa__activa=True,
        rol__in=[RolEmpresa.DUENO, RolEmpresa.ADMINISTRADOR_SEDE, RolEmpresa.CAJERO],
    ).exists()
    if not autorizado:
        raise PermissionDenied("Tu cuenta no tiene permisos para consultar reservas de una sede.")


class SolicitudReservaView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        entrada = SolicitarReservaEntrada(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        reserva, creada = crear_retencion(
            request.user,
            datos["cancha_id"],
            datos["fecha"],
            datos["hora_inicio"],
            datos["duracion_horas"],
            datos["clave_idempotencia"],
        )
        respuesta = ReservaLecturaSerializer(reserva).data
        return Response(respuesta, status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK)


class MisReservasView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        queryset = Reserva.objects.filter(jugador=request.user).select_related(
            "cancha", "cancha__sede", "cancha__sede__empresa", "jugador"
        )
        return _pagina(request, queryset, administrativa=False)


class ReservaPropiaView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, codigo: str) -> Response:
        reserva = get_object_or_404(
            Reserva.objects.filter(jugador=request.user).select_related(
                "cancha", "cancha__sede", "cancha__sede__empresa"
            ), codigo=codigo,
        )
        return Response(ReservaLecturaSerializer(reserva).data)


class CancelarReservaPropiaView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def post(self, request: Request, codigo: str) -> Response:
        reserva = cancelar_retencion(request.user, codigo)
        if reserva is None:
            return Response({"detail": "No se encontró esa reserva en tu cuenta."}, status=404)
        return Response(ReservaLecturaSerializer(reserva).data)


class ReservasAdministrativasView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        _exigir_personal(request.user)
        entrada = FiltrosReservasEntrada(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        canchas = canchas_visibles(request.user)
        queryset = Reserva.objects.filter(cancha__in=canchas).select_related(
            "cancha", "cancha__sede", "cancha__sede__empresa", "jugador"
        )
        if datos.get("desde"):
            queryset = queryset.filter(inicio__date__gte=datos["desde"])
        if datos.get("hasta"):
            queryset = queryset.filter(inicio__date__lte=datos["hasta"])
        if datos.get("estado"):
            queryset = queryset.filter(estado=datos["estado"])
        if datos.get("cancha"):
            queryset = queryset.filter(cancha_id=datos["cancha"])
        if datos.get("sede"):
            queryset = queryset.filter(cancha__sede_id=datos["sede"])
        if datos.get("empresa"):
            queryset = queryset.filter(cancha__sede__empresa_id=datos["empresa"])
        if datos.get("q"):
            termino = datos["q"]
            queryset = queryset.filter(
                Q(codigo__icontains=termino)
                | Q(cancha__nombre__icontains=termino)
                | Q(jugador__username__icontains=termino)
                | Q(jugador__email__icontains=termino)
            )
        return _pagina(request, queryset, administrativa=True)


class ReservaAdministrativaDetalleView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, codigo: str) -> Response:
        _exigir_personal(request.user)
        reserva = get_object_or_404(
            Reserva.objects.filter(cancha__in=canchas_visibles(request.user)).select_related(
                "cancha", "cancha__sede", "cancha__sede__empresa", "jugador"
            ), codigo=codigo,
        )
        _auditar_consulta_global(
            request, "consultar_reserva_global", reserva.pk,
            {"codigo": reserva.codigo},
        )
        return Response(ReservaLecturaSerializer(reserva, context={"administrativa": True}).data)


class DisponibilidadReservasAdminView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, cancha_id: int) -> Response:
        _exigir_personal(request.user)
        entrada = DisponibilidadEntrada(data=request.query_params)
        entrada.is_valid(raise_exception=True)
        cancha = get_object_or_404(canchas_visibles(request.user), pk=cancha_id)
        datos = entrada.validated_data
        resultado = consultar_disponibilidad_reservable(
            cancha, datos["desde"], datos["hasta"], usuario=request.user
        )
        return Response(resultado)


def _pagina(request: Request, queryset: QuerySet, *, administrativa: bool) -> Response:
    if administrativa:
        filtros = {
            llave: request.query_params[llave]
            for llave in ("desde", "hasta", "estado", "cancha", "sede", "empresa")
            if llave in request.query_params
        }
        _auditar_consulta_global(request, "consultar_reservas_globales", None, filtros)
    pagina = PaginacionReservas()
    resultados = pagina.paginate_queryset(queryset, request)
    serializador = ReservaLecturaSerializer(
        resultados, many=True, context={"administrativa": administrativa}
    )
    return pagina.get_paginated_response(serializador.data)


def _auditar_consulta_global(request, accion: str, recurso_id: int | None, datos: dict) -> None:
    if request.user.is_superuser:
        RegistroAuditoria.objects.create(
            actor=request.user,
            accion=accion,
            recurso="reservas",
            recurso_id=recurso_id,
            datos=datos,
        )
