"""Configuración compartida para tests de integración.

Este módulo proporciona fixtures para tests de integración que
verifican la API REST sin necesidad de servidor corriendo.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def client():
    """Fixture que proporciona un TestClient para la aplicación FastAPI.

    El cliente se crea fresh para cada test, asegurando aislamiento.
    No requiere servidor corriendo - usa el transport de pruebas de Starlette.

    Returns:
        TestClient: Cliente HTTP de pruebas configurado con la app
    """
    return TestClient(app)
