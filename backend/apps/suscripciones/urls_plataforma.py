from django.urls import path

from apps.suscripciones.views import (
    ConfiguracionSuscripcionView,
    EstadoSuscripcionView,
    PlanesView,
    PlanView,
    ResolverSolicitudView,
    SolicitudesSuscripcionView,
)

urlpatterns = [
    path("planes/", PlanesView.as_view()),
    path("planes/<int:plan_id>/", PlanView.as_view()),
    path("solicitudes/", SolicitudesSuscripcionView.as_view()),
    path("solicitudes/<int:solicitud_id>/resolver/", ResolverSolicitudView.as_view()),
    path("empresas/<int:empresa_id>/suscripcion/estado/", EstadoSuscripcionView.as_view()),
    path("suscripciones/configuracion/", ConfiguracionSuscripcionView.as_view()),
]
