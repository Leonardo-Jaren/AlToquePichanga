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
from apps.reservas.views_asistencia import IngresoReservaView
from apps.reservas.views_cancelacion import (
    CancelarReservaAdministrativaView,
    CancelarReservaView,
)
from apps.reservas.views_ticket import TicketPropioView, TicketQrPropioView

urlpatterns = [
    path("", SolicitudReservaView.as_view(), name="solicitar-reserva"),
    path("mias/", MisReservasView.as_view(), name="mis-reservas"),
    path("administracion/ingreso/<str:accion>/", IngresoReservaView.as_view(), name="ingreso-reserva"),
    path("administracion/", ReservasAdministrativasView.as_view(), name="reservas-administrativas"),
    path("administracion/disponibilidad/<int:cancha_id>/", DisponibilidadReservasAdminView.as_view(), name="disponibilidad-reservas-admin"),
    path("administracion/<str:codigo>/cancelar/", CancelarReservaAdministrativaView.as_view(), name="cancelar-reserva-admin"),
    path("<str:codigo>/cancelacion/", CancelarReservaView.as_view(), name="cancelar-reserva"),
    path("administracion/<str:codigo>/", ReservaAdministrativaDetalleView.as_view(), name="detalle-reserva-admin"),
    path("<str:codigo>/ticket/", TicketPropioView.as_view(), name="ticket-reserva-propia"),
    path("<str:codigo>/ticket/qr/", TicketQrPropioView.as_view(), name="qr-reserva-propia"),
    path("<str:codigo>/", ReservaPropiaView.as_view(), name="detalle-reserva-propia"),
    path("<str:codigo>/cancelar/", CancelarReservaPropiaView.as_view(), name="cancelar-reserva-propia"),
]
