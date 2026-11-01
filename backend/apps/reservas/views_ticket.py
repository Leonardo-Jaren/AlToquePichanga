from typing import ClassVar

from django.http import HttpResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reservas.services.ticket import datos_ticket, qr_ticket_svg, reserva_ticket


class TicketPropioView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, codigo: str) -> Response:
        return Response(datos_ticket(reserva_ticket(request.user, codigo)))


class TicketQrPropioView(APIView):
    permission_classes: ClassVar[list] = [IsAuthenticated]

    def get(self, request: Request, codigo: str) -> HttpResponse:
        svg = qr_ticket_svg(reserva_ticket(request.user, codigo))
        respuesta = HttpResponse(svg, content_type="image/svg+xml")
        respuesta["Cache-Control"] = "no-store"
        respuesta["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return respuesta
