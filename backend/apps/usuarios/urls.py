from django.urls import path

from .views.autenticacion import (
    CsrfView,
    LoginView,
    LogoutView,
    PerfilView,
    RecuperarView,
    RegistroView,
    RestablecerView,
    VerificarView,
)
from .views.google import GoogleIniciarView, GoogleRetornoView

urlpatterns = [
    path("google/iniciar/", GoogleIniciarView.as_view()),
    path("google/retorno/", GoogleRetornoView.as_view()),
    path("csrf/", CsrfView.as_view()),
    path("registro/", RegistroView.as_view()),
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("perfil/", PerfilView.as_view()),
    path("recuperar/", RecuperarView.as_view()),
    path("restablecer/", RestablecerView.as_view()),
    path("verificar-correo/", VerificarView.as_view()),
]
