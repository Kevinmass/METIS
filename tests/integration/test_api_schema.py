from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)
HTTP_OK = 200


def test_validate_response_contains_required_schema_fields():
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
    response = client.post("/validate", json={"series": [1.0, 2.0, 3.0, 4.0, 5.0]})

    assert response.status_code == HTTP_OK
    validation = response.json()["validation"]

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
