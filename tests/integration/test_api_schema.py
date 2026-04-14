"""Tests de validación del schema de respuesta de la API.

Este módulo verifica que la estructura de la respuesta de /validate
cumpla con el contrato establecido. Estos tests son contratos de
estructura que detectan cambios incompatibles en la API.

Cobertura:
    - Campos raíz obligatorios (n, warnings, validation)
    - Grupos de validación presentes (independence, homogeneity, trend, outliers)
    - Campos obligatorios en cada resultado de prueba
      (statistic, critical_value, alpha, verdict)

Importancia:
    Cualquier falla aquí indica que el contrato de API cambió,
    lo cual puede romper compatibilidad con el frontend o GeoAI.
"""

from fastapi.testclient import TestClient

from api.main import app


# Cliente de test para la aplicación FastAPI
client = TestClient(app)

# Constantes HTTP
HTTP_OK = 200


def test_validate_response_contains_required_schema_fields():
    """Verifica que la respuesta contenga todos los campos raíz requeridos.

    Valida presencia de:
        - n: cantidad de observaciones
        - warnings: lista de advertencias
        - validation: objeto con grupos de resultados
        - validation.independence, .homogeneity, .trend, .outliers

    Esta estructura es el contrato base que consume el frontend.
    """
    response = client.post("/validate", json={"series": [1.0, 2.0, 3.0, 4.0, 5.0]})

    assert response.status_code == HTTP_OK
    payload = response.json()

    assert "n" in payload
    assert "warnings" in payload
    assert "validation" in payload
    assert "independence" in payload["validation"]
    assert "homogeneity" in payload["validation"]
    assert "trend" in payload["validation"]
    assert "outliers" in payload["validation"]


def test_each_test_result_contains_required_fields():
    """Verifica que cada resultado individual tenga los campos obligatorios.

    Itera sobre los 8 resultados individuales (2 independencia + 3 homogeneidad +
    2 tendencia + 1 outliers) y verifica que todos contengan:
        - statistic: valor numérico calculado
        - critical_value: valor de referencia
        - alpha: nivel de significancia
        - verdict: veredicto final

    Esto asegura que todos los grupos retornan información completa.
    """
    response = client.post("/validate", json={"series": [1.0, 2.0, 3.0, 4.0, 5.0]})

    assert response.status_code == HTTP_OK
    validation = response.json()["validation"]

    # Lista de todos los nodos de resultado en la respuesta
    result_nodes = [
        validation["independence"]["anderson"],
        validation["independence"]["wald_wolfowitz"],
        validation["homogeneity"]["helmert"],
        validation["homogeneity"]["t_student"],
        validation["homogeneity"]["cramer"],
        validation["trend"]["mann_kendall"],
        validation["trend"]["kolmogorov_smirnov"],
        validation["outliers"]["chow"],
    ]

    for result in result_nodes:
        assert "statistic" in result
        assert "critical_value" in result
        assert "alpha" in result
        assert "verdict" in result
