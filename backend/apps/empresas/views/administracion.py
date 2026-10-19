from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empresas.models import EstadoEmpresa
from apps.empresas.serializers import (
    EmpresaEntrada,
    EntradaEstricta,
)
from apps.empresas.services import empresas
from apps.empresas.services.acceso import consultar_empresa, consultar_empresas
from apps.empresas.services.empresas import cambiar_estado_empresa


class PaginacionEmpresas(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class EstadoEmpresaEntrada(EntradaEstricta):
    estado = serializers.ChoiceField(choices=EstadoEmpresa.choices)


class EmpresasView(APIView):
    def get(self, request):
        return Response(consultar_empresas(request.user))

    def post(self, request):
        serializer = EmpresaEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(empresas.crear_empresa(request.user, serializer.validated_data), status=201)


class EmpresaView(APIView):
    def get(self, request, identificador: int):
        return Response(consultar_empresa(request.user, identificador))


class EmpresasAdministradasView(APIView):
    def get(self, request):
        consulta = request.query_params.get("q", "").strip()[:100]
        datos = empresas.consulta_empresas_propias(request.user, consulta)
        paginador = PaginacionEmpresas()
        pagina = paginador.paginate_queryset(datos, request, view=self)
        filas = [empresas.datos_empresa_propietaria(item) for item in pagina]
        return paginador.get_paginated_response(filas)


class EmpresaAdministradaView(APIView):
    def get(self, request, identificador: int):
        return Response(empresas.consultar_empresa_propietaria(request.user, identificador))

    def patch(self, request, identificador: int):
        modelo = empresas.modelo_empresa_propietaria(request.user, identificador)
        serializer = EmpresaEntrada(data=request.data, partial=True, context={"empresa": modelo})
        serializer.is_valid(raise_exception=True)
        resultado = empresas.actualizar_empresa(
            request.user, identificador, serializer.validated_data
        )
        return Response(resultado)


class EmpresasPlataformaView(APIView):
    def get(self, request):
        consulta = request.query_params.get("q", "").strip()[:100]
        estado = request.query_params.get("estado", "").strip()
        datos = empresas.consulta_empresas_plataforma(request.user, consulta, estado)
        paginador = PaginacionEmpresas()
        pagina = paginador.paginate_queryset(datos, request, view=self)
        filas = [empresas.datos_empresa_plataforma(item) for item in pagina]
        return paginador.get_paginated_response(filas)


class EmpresaPlataformaView(APIView):
    def get(self, request, identificador: int):
        return Response(empresas.consultar_empresa_plataforma(request.user, identificador))

    def patch(self, request, identificador: int):
        serializer = EstadoEmpresaEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(cambiar_estado_empresa(
            request.user, identificador, serializer.validated_data["estado"]
        ))
