from django.urls import path

from apps.canchas.views import (
    CanchasView,
    CanchaView,
    EstadoCanchaView,
    ImagenesCanchaView,
    RetirarImagenCanchaView,
)
from apps.horarios.views import DisponibilidadOperativaView, HorarioCanchaView
from apps.tarifas.urls import urlpatterns as rutas_tarifas

urlpatterns = [
    path("", CanchasView.as_view(), name="canchas"),
    path("<int:cancha_id>/", CanchaView.as_view(), name="cancha"),
    path("<int:cancha_id>/horario-semanal/", HorarioCanchaView.as_view()),
    path("<int:cancha_id>/disponibilidad-operativa/", DisponibilidadOperativaView.as_view()),
    path("<int:cancha_id>/estado/", EstadoCanchaView.as_view(), name="estado-cancha"),
    path("<int:cancha_id>/imagenes/", ImagenesCanchaView.as_view(), name="imagenes-cancha"),
    path(
        "<int:cancha_id>/imagenes/<int:imagen_id>/retirar/",
        RetirarImagenCanchaView.as_view(),
        name="retirar-imagen-cancha",
    ),
]

urlpatterns += rutas_tarifas
