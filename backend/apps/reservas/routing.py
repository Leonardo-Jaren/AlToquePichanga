from django.urls import path

from apps.reservas.consumers.disponibilidad import DisponibilidadConsumer

websocket_urlpatterns = [
    path("ws/disponibilidad/", DisponibilidadConsumer.as_asgi()),
]
