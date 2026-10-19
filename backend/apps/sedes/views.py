from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empresas.serializers import EntradaEstricta
from apps.sedes.serializers import ImagenSedeEntrada, SedeEntrada
from apps.sedes.services.sedes import (
    actualizar_sede,
    agregar_imagen,
    cambiar_estado_sede,
    consultar_sede,
    crear_sede,
    listar_sedes,
    retirar_imagen,
    sede_editable,
)


class EstadoSedeEntrada(EntradaEstricta):
    activa = serializers.BooleanField()
    confirmar = serializers.BooleanField()


class SedesView(APIView):
    def get(self, request):
        empresa_id = request.query_params.get("empresa")
        if empresa_id is not None:
            try:
                empresa_id = int(empresa_id)
            except ValueError:
                raise ValidationError({"empresa": "El identificador no es válido."}) from None
        return Response(listar_sedes(request.user, empresa_id))

    def post(self, request):
        serializer = SedeEntrada(data=request.data, context={"creando": True})
        serializer.is_valid(raise_exception=True)
        return Response(crear_sede(request.user, serializer.validated_data), status=201)


class SedeView(APIView):
    def get(self, request, sede_id: int):
        return Response(consultar_sede(request.user, sede_id))

    def patch(self, request, sede_id: int):
        sede = sede_editable(request.user, sede_id)
        serializer = SedeEntrada(
            data=request.data, partial=True, context={"sede": sede}
        )
        serializer.is_valid(raise_exception=True)
        return Response(actualizar_sede(request.user, sede_id, serializer.validated_data))


class EstadoSedeView(APIView):
    def post(self, request, sede_id: int):
        serializer = EstadoSedeEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        datos = serializer.validated_data
        if not datos["confirmar"]:
            raise ValidationError({"confirmar": "Confirma el cambio de estado."})
        return Response(cambiar_estado_sede(request.user, sede_id, datos["activa"]))


class ImagenesSedeView(APIView):
    def post(self, request, sede_id: int):
        serializer = ImagenSedeEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(agregar_imagen(request.user, sede_id, serializer.validated_data), status=201)


class RetirarImagenSedeView(APIView):
    def post(self, request, sede_id: int, imagen_id: int):
        serializer = ConfirmarEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmar"]:
            raise ValidationError({"confirmar": "Confirma el retiro de la imagen."})
        return Response(retirar_imagen(request.user, sede_id, imagen_id))


class ConfirmarEntrada(EntradaEstricta):
    confirmar = serializers.BooleanField()
