from django.urls import path

from apps.canchas.views_publicas import (
    CanchaPublicaView,
    CanchasPublicasView,
    CotizacionCanchaPublicaView,
    DisponibilidadCanchaPublicaView,
)

urlpatterns = [
    path("", CanchasPublicasView.as_view(), name="canchas-publicas"),
    path("<int:cancha_id>/", CanchaPublicaView.as_view(), name="cancha-publica"),
    path(
        "<int:cancha_id>/disponibilidad/",
        DisponibilidadCanchaPublicaView.as_view(),
        name="disponibilidad-cancha-publica",
    ),
    path(
        "<int:cancha_id>/cotizar/",
        CotizacionCanchaPublicaView.as_view(),
        name="cotizar-cancha-publica",
    ),
]
