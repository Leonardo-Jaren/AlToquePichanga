"""
Vistas compartidas transversales para la API de AlToque Pichanga.
"""

from django.db import DatabaseError, OperationalError, connection
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """
    Endpoint para verificación de estado del backend y conectividad a base de datos.
    """

    authentication_classes = ()
    permission_classes = ()

    def get(self, request):
        db_status = "desconectada"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                row = cursor.fetchone()
                if row and row[0] == 1:
                    db_status = "conectada"
        except (DatabaseError, OperationalError):
            db_status = "error de conexión"

        datos = {
            "estado": "operativo" if db_status == "conectada" else "degradado",
            "servicio": "AlToque Pichanga API",
            "version": "0.1.0",
            "fase": "Fase 0 - Inicialización",
            "base_de_datos": db_status,
            "timestamp": timezone.now().isoformat(),
        }

        codigo_http = (
            status.HTTP_200_OK
            if db_status == "conectada"
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(datos, status=codigo_http)
