from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.empresas.serializers import EntradaEstricta
from apps.empresas.serializers_personal import PersonalEntrada
from apps.empresas.services.personal import (
    aceptar_invitacion,
    invitar_personal,
    listar_personal,
    revocar_invitacion,
    revocar_personal,
)


class RevocarEntrada(EntradaEstricta):
    confirmar = serializers.BooleanField()


class TokenInvitacionEntrada(EntradaEstricta):
    token = serializers.CharField(max_length=100)


class PersonalEmpresaView(APIView):
    def get(self, request, empresa_id: int):
        return Response(listar_personal(request.user, empresa_id))

    def post(self, request, empresa_id: int):
        serializer = PersonalEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        resultado = invitar_personal(request.user, empresa_id, serializer.validated_data)
        return Response(resultado, status=201 if resultado["tipo"] == "invitacion" else 200)


class InvitacionPersonalView(APIView):
    def post(self, request, empresa_id: int):
        serializer = PersonalEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        resultado = invitar_personal(request.user, empresa_id, serializer.validated_data)
        return Response(resultado, status=201 if resultado["tipo"] == "invitacion" else 200)


class RevocarPersonalView(APIView):
    def post(self, request, empresa_id: int, membresia_id: int):
        serializer = RevocarEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmar"]:
            raise ValidationError({"confirmar": "Confirma la revocación del acceso."})
        return Response(revocar_personal(request.user, empresa_id, membresia_id))


class RevocarInvitacionView(APIView):
    def post(self, request, empresa_id: int, invitacion_id: int):
        serializer = RevocarEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not serializer.validated_data["confirmar"]:
            raise ValidationError({"confirmar": "Confirma la cancelación de la invitación."})
        return Response(revocar_invitacion(request.user, empresa_id, invitacion_id))


class AceptarInvitacionView(APIView):
    def post(self, request):
        serializer = TokenInvitacionEntrada(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(aceptar_invitacion(request.user, serializer.validated_data["token"]))
