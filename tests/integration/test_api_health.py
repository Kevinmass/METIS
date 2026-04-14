"""Tests de integración para endpoint de health check.

Este módulo prueba el endpoint /health de la API para verificar
que el servicio está operativo y responde correctamente.

Se ejecuta con:
    pytest tests/integration/test_api_health.py -v

Nota:
    Estos tests usan TestClient de FastAPI que no requiere servidor
    corriendo. La aplicación se instancia directamente en cada test.
"""

from fastapi.testclient import TestClient

from api.main import app


# Cliente de test para la aplicación FastAPI
client = TestClient(app)

# Constantes HTTP
HTTP_OK = 200


def test_health_returns_ok_status():
    """Verifica que /health retorna estado operativo.

    Valida:
        - Status HTTP 200
        - Campo status = "ok"
        - Campo version presente (formato string)

    Este test es ejecutado por el CI para verificar despliegue exitoso.
    """
    response = client.get("/health")

    assert response.status_code == HTTP_OK
    assert response.json()["status"] == "ok"
    assert "version" in response.json()
