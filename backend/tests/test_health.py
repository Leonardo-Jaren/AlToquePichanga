"""
Pruebas automatizadas para el endpoint de salud y conectividad de base de datos.
"""

import pytest
from django.db import connection
from django.urls import reverse
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_health_check_endpoint_retorna_200_y_estructura_valida(api_client):
    """
    Verifica que el endpoint /api/health/ devuelva 200 OK y la estructura esperada.
    """
    url = reverse("health_check")
    response = api_client.get(url)

    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "operativo"
    assert data["servicio"] == "AlToque Pichanga API"
    assert data["version"] == "0.1.0"
    assert data["fase"] == "Fase 0 - Inicialización"
    assert data["base_de_datos"] == "conectada"
    assert "timestamp" in data


@pytest.mark.django_db
def test_conexion_activa_postgresql():
    """
    Verifica que Django ejecute consultas contra la base de datos PostgreSQL real.
    """
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 + 1 AS resultado;")
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == 2
