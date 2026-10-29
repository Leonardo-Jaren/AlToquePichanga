from django.urls import path

from apps.tarifas.views import (
    CalcularPrecioView,
    EstadoReglaTarifaView,
    ReglaTarifaView,
    TarifasCanchaView,
)

urlpatterns = [
    path("<int:cancha_id>/tarifas/", TarifasCanchaView.as_view(), name="tarifas-cancha"),
    path(
        "<int:cancha_id>/tarifas/<int:tarifa_id>/",
        ReglaTarifaView.as_view(), name="tarifa-cancha",
    ),
    path(
        "<int:cancha_id>/tarifas/<int:tarifa_id>/estado/",
        EstadoReglaTarifaView.as_view(), name="estado-tarifa-cancha",
    ),
    path(
        "<int:cancha_id>/calcular-precio/",
        CalcularPrecioView.as_view(), name="calcular-precio-cancha",
    ),
]
