from django.conf import settings
from django.shortcuts import redirect
from google.auth.exceptions import GoogleAuthError
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from apps.usuarios.serializers.autenticacion import EntradaEstricta
from apps.usuarios.services.google import completar_google, iniciar_google
from apps.usuarios.views.autenticacion import Publica, entrada


class GoogleEntrada(EntradaEstricta):
    vincular = serializers.BooleanField(default=False)


class GoogleIniciarView(Publica):
    def post(self, request):
        self.limitar_ip(request, "google", settings.AUTH_PUBLIC_LIMIT)
        return Response({"url": iniciar_google(request, entrada(GoogleEntrada, request)["vincular"])})


class GoogleRetornoView(Publica):
    def get(self, request):
        try:
            completar_google(request)
        except (APIException, GoogleAuthError):
            return redirect(f"{settings.FRONTEND_URL}/google-retorno?error=autorizacion")
        return redirect(f"{settings.FRONTEND_URL}/google-retorno")
