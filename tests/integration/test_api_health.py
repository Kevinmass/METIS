from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)
HTTP_OK = 200


def test_health_returns_ok_status():
    response = client.get("/health")

    assert response.status_code == HTTP_OK
    assert response.json()["status"] == "ok"
    assert "version" in response.json()
