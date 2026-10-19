from django.conf import settings
from django.middleware.csrf import get_token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.serializers.autenticacion import (
    CorreoEntrada,
    LoginEntrada,
    PerfilEntrada,
    RegistroEntrada,
    RestablecerEntrada,
    TokenEntrada,
)
from apps.usuarios.services import autenticacion, correos, perfil
from apps.usuarios.services.seguridad import limitar


def entrada(clase, request) -> dict:
    serializer = clase(data=request.data)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


class Publica(APIView):
    permission_classes = (AllowAny,)

    def limitar_ip(self, request, ambito: str, maximo: int) -> None:
        limitar(ambito, request.META.get("REMOTE_ADDR", ""), maximo)


class CsrfView(Publica):
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class RegistroView(Publica):
    def post(self, request):
        self.limitar_ip(request, "registro", settings.AUTH_PUBLIC_LIMIT)
        return Response(autenticacion.registrar(request, entrada(RegistroEntrada, request)), status=201)


class LoginView(Publica):
    def post(self, request):
        self.limitar_ip(request, "login_ip", settings.AUTH_LOGIN_IP_LIMIT)
        datos = entrada(LoginEntrada, request)
        limitar("login_correo", datos["correo"], settings.AUTH_LOGIN_LIMIT)
        return Response(autenticacion.iniciar_sesion(request, datos))


class LogoutView(APIView):
    def post(self, request):
        autenticacion.cerrar_sesion(request)
        return Response(status=204)


class PerfilView(APIView):
    def get(self, request):
        return Response(perfil.datos_usuario(request.user))

    def patch(self, request):
        return Response(perfil.actualizar_perfil(request.user, entrada(PerfilEntrada, request)))


class RecuperarView(Publica):
    def post(self, request):
        self.limitar_ip(request, "recuperacion", settings.AUTH_PUBLIC_LIMIT)
        correos.solicitar_recuperacion(entrada(CorreoEntrada, request)["correo"])
        return Response({"mensaje": "Si el correo corresponde a una cuenta, recibirás un enlace."})


class RestablecerView(Publica):
    def post(self, request):
        self.limitar_ip(request, "restablecer", settings.AUTH_PUBLIC_LIMIT)
        autenticacion.restablecer(entrada(RestablecerEntrada, request))
        return Response({"mensaje": "Contraseña actualizada. Ya puedes iniciar sesión."})


class VerificarView(Publica):
    def post(self, request):
        self.limitar_ip(request, "verificar", settings.AUTH_PUBLIC_LIMIT)
        autenticacion.verificar_correo(entrada(TokenEntrada, request))
        return Response({"mensaje": "Correo verificado."})
