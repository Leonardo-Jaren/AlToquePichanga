from django.urls import path

from apps.pagos.views import (
    DeclararComprobantePropioView,
    MediosPagoSedeView,
    PagoAdministracionDetalleView,
    PagoReservaPropiaView,
    PagosAdministracionView,
    RevisarPagoAdministracionView,
    SolicitudPagoPropiaView,
)

urlpatterns = [
    path("sedes/<int:sede_id>/medios/", MediosPagoSedeView.as_view(), name="medios-pago-sede"),
    path("reservas/<str:codigo>/", PagoReservaPropiaView.as_view(), name="pago-reserva-propia"),
    path("reservas/<str:codigo>/solicitudes/", SolicitudPagoPropiaView.as_view(), name="solicitud-pago-reserva"),
    path("reservas/<str:codigo>/<int:pago_id>/declarar/", DeclararComprobantePropioView.as_view(), name="declarar-comprobante"),
    path("administracion/", PagosAdministracionView.as_view(), name="pagos-administrativos"),
    path("administracion/<int:pago_id>/", PagoAdministracionDetalleView.as_view(), name="detalle-pago-administrativo"),
    path("administracion/<int:pago_id>/<str:accion>/", RevisarPagoAdministracionView.as_view(), name="revisar-pago-administrativo"),
]
