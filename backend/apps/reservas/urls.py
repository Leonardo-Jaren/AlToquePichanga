from django.urls import path

from apps.reservas.views import (
    CancelarReservaPropiaView,
    DisponibilidadReservasAdminView,
    MisReservasView,
    ReservaAdministrativaDetalleView,
    ReservaPropiaView,
    ReservasAdministrativasView,
    SolicitudReservaView,
)

urlpatterns = [
    path("", SolicitudReservaView.as_view(), name="solicitar-reserva"),
    path("mias/", MisReservasView.as_view(), name="mis-reservas"),
    path("administracion/", ReservasAdministrativasView.as_view(), name="reservas-administrativas"),
    path("administracion/disponibilidad/<int:cancha_id>/", DisponibilidadReservasAdminView.as_view(), name="disponibilidad-reservas-admin"),
    path("administracion/<str:codigo>/", ReservaAdministrativaDetalleView.as_view(), name="detalle-reserva-admin"),
    path("<str:codigo>/", ReservaPropiaView.as_view(), name="detalle-reserva-propia"),
    path("<str:codigo>/cancelar/", CancelarReservaPropiaView.as_view(), name="cancelar-reserva-propia"),
]
