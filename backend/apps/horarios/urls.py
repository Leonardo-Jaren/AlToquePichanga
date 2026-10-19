from django.urls import path

from apps.horarios.views import AnularExcepcionHorarioView, ExcepcionesHorarioView

urlpatterns = [
    path("excepciones/", ExcepcionesHorarioView.as_view(), name="excepciones-horario"),
    path(
        "excepciones/<int:excepcion_id>/anular/",
        AnularExcepcionHorarioView.as_view(),
        name="anular-excepcion-horario",
    ),
]
