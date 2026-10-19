from django.urls import path

from apps.horarios.views import HorarioSedeView
from apps.sedes.views import (
    EstadoSedeView,
    ImagenesSedeView,
    RetirarImagenSedeView,
    SedesView,
    SedeView,
)

urlpatterns = [
    path("", SedesView.as_view()),
    path("<int:sede_id>/", SedeView.as_view()),
    path("<int:sede_id>/horario-semanal/", HorarioSedeView.as_view()),
    path("<int:sede_id>/estado/", EstadoSedeView.as_view()),
    path("<int:sede_id>/imagenes/", ImagenesSedeView.as_view()),
    path("<int:sede_id>/imagenes/<int:imagen_id>/retirar/", RetirarImagenSedeView.as_view()),
]
