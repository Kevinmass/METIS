"""Tests de integración para la API de análisis de frecuencia.

Este módulo contiene tests que verifican la integración correcta
entre la API REST y el core de análisis de frecuencia.
"""


class TestFrequencyFitEndpoint:
    """Tests para endpoint POST /frequency/fit."""

    def test_frequency_fit_valid_series(self, client):
        """Test de ajuste de distribuciones con serie válida."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0, 115.0, 98.0, 102.0],
            "estimation_method": "MOM",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 200
        data = response.json()

        assert "n" in data
        assert data["n"] == 8
        assert "estimation_method" in data
        assert data["estimation_method"] == "MOM"
        assert "distributions" in data
        assert len(data["distributions"]) > 0
        assert "recommended_distribution" in data

    def test_frequency_fit_specific_distributions(self, client):
        """Test de ajuste de distribuciones específicas."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "MOM",
            "distribution_names": ["Normal", "Gumbel"],
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 200
        data = response.json()

        assert len(data["distributions"]) <= 2
        dist_names = [d["distribution_name"] for d in data["distributions"]]
        assert all(name in ["Normal", "Gumbel"] for name in dist_names)

    def test_frequency_fit_empty_series(self, client):
        """Test de ajuste con serie vacía."""
        request = {
            "series": [],
            "estimation_method": "MOM",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 400
        assert "at least" in response.json()["detail"].lower()

    def test_frequency_fit_too_short(self, client):
        """Test de ajuste con serie demasiado corta."""
        request = {
            "series": [1.0, 2.0],
            "estimation_method": "MOM",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 400
        assert "at least" in response.json()["detail"].lower()

    def test_frequency_fit_with_nan(self, client):
        """Test de ajuste con valores NaN."""
        request = {
            "series": [100.0, 120.0, None, 110.0, 105.0, 115.0, 98.0, 102.0],
            "estimation_method": "MOM",
        }

        response = client.post("/frequency/fit", json=request)

        # La API debería rechazar datos no numéricos con 422
        assert response.status_code == 422

    def test_frequency_fit_distribution_schema(self, client):
        """Test de que cada distribución tiene el schema correcto."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "MOM",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 200
        data = response.json()

        for dist in data["distributions"]:
            assert "distribution_name" in dist
            assert "parameters" in dist
            assert "estimation_method" in dist
            assert "goodness_of_fit" in dist
            assert "is_recommended" in dist

            # Verificar estructura de goodness_of_fit
            gof = dist["goodness_of_fit"]
            assert "chi_square" in gof
            assert "chi_square_p_value" in gof
            assert "chi_square_verdict" in gof
            assert "ks_statistic" in gof
            assert "ks_p_value" in gof
            assert "ks_verdict" in gof
            assert "eea" in gof
            assert "eea_verdict" in gof

    def test_frequency_fit_mle_method(self, client):
        """Test de ajuste con método MLE."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "MLE",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["estimation_method"] == "MLE"

    def test_frequency_fit_mentropy_method(self, client):
        """Test de ajuste con método MEnt."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "MEnt",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["estimation_method"] == "MEnt"

    def test_frequency_fit_invalid_method(self, client):
        """Test de ajuste con método inválido."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "INVALID",
        }

        response = client.post("/frequency/fit", json=request)

        # Debería dar error de validación de Pydantic
        assert response.status_code == 422


class TestDesignEventEndpoint:
    """Tests para endpoint POST /frequency/design-event."""

    def test_design_event_valid(self, client):
        """Test de cálculo de evento de diseño válido."""
        request = {
            "distribution_name": "Normal",
            "parameters": {"mu": 100.0, "sigma": 20.0},
            "return_period": 100.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 200
        data = response.json()

        assert "return_period" in data
        assert data["return_period"] == 100.0
        assert "annual_probability" in data
        assert data["annual_probability"] == 0.99
        assert "design_value" in data
        assert "distribution_name" in data
        assert "parameters" in data

    def test_design_event_t50(self, client):
        """Test de cálculo de evento de diseño para T=50."""
        request = {
            "distribution_name": "Normal",
            "parameters": {"mu": 100.0, "sigma": 20.0},
            "return_period": 50.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["return_period"] == 50.0
        assert data["annual_probability"] == 0.98

    def test_design_event_invalid_return_period(self, client):
        """Test de cálculo con período de retorno inválido."""
        request = {
            "distribution_name": "Normal",
            "parameters": {"mu": 100.0, "sigma": 20.0},
            "return_period": -10.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 400
        assert "positive" in response.json()["detail"].lower()

    def test_design_event_zero_return_period(self, client):
        """Test de cálculo con período de retorno cero."""
        request = {
            "distribution_name": "Normal",
            "parameters": {"mu": 100.0, "sigma": 20.0},
            "return_period": 0.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 400

    def test_design_event_invalid_distribution(self, client):
        """Test de cálculo con distribución inválida."""
        request = {
            "distribution_name": "InvalidDistribution",
            "parameters": {"mu": 100.0, "sigma": 20.0},
            "return_period": 100.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 422
        assert "not found" in response.json()["detail"].lower()

    def test_design_event_logpearson3(self, client):
        """Test de cálculo con distribución Log-Pearson III."""
        request = {
            "distribution_name": "Log-Pearson III",
            "parameters": {"mu": 2.0, "sigma": 0.5, "gamma": 0.1},
            "return_period": 100.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["distribution_name"] == "Log-Pearson III"
        assert data["design_value"] > 0  # Log-Pearson III debe dar valores positivos

    def test_design_event_gumbel(self, client):
        """Test de cálculo con distribución Gumbel."""
        request = {
            "distribution_name": "Gumbel",
            "parameters": {"xi": 100.0, "alpha": 20.0},
            "return_period": 100.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["distribution_name"] == "Gumbel"


class TestAPIIntegration:
    """Tests de integración completa de la API."""

    def test_fit_then_design_event_workflow(self, client):
        """Test de flujo completo: ajuste y luego evento de diseño."""
        # 1. Ajustar distribuciones
        fit_request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0, 115.0, 98.0, 102.0],
            "estimation_method": "MOM",
        }

        fit_response = client.post("/frequency/fit", json=fit_request)
        assert fit_response.status_code == 200
        fit_data = fit_response.json()

        # 2. Obtener distribución recomendada
        recommended = fit_data["recommended_distribution"]
        assert recommended is not None

        # 3. Calcular evento de diseño con esa distribución
        design_request = {
            "distribution_name": recommended["distribution_name"],
            "parameters": recommended["parameters"],
            "return_period": 100.0,
        }

        design_response = client.post("/frequency/design-event", json=design_request)
        assert design_response.status_code == 200
        design_data = design_response.json()

        assert design_data["return_period"] == 100.0
        assert design_data["design_value"] > 0

    def test_multiple_return_periods(self, client):
        """Test de cálculo de múltiples eventos de diseño."""
        # Primero ajustar
        fit_request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "MOM",
        }

        fit_response = client.post("/frequency/fit", json=fit_request)
        fit_data = fit_response.json()
        recommended = fit_data["recommended_distribution"]

        # Calcular eventos para múltiples períodos
        return_periods = [2, 5, 10, 25, 50, 100]
        design_values = []

        for t in return_periods:
            design_request = {
                "distribution_name": recommended["distribution_name"],
                "parameters": recommended["parameters"],
                "return_period": t,
            }

            design_response = client.post(
                "/frequency/design-event", json=design_request
            )
            assert design_response.status_code == 200
            design_data = design_response.json()
            design_values.append(design_data["design_value"])

        # Verificar que los valores crecen con el período
        assert design_values == sorted(design_values)


class TestAPIErrorHandling:
    """Tests de manejo de errores de la API."""

    def test_missing_required_field(self, client):
        """Test de error por campo faltante."""
        request = {
            "series": [100.0, 120.0, 95.0],
            # Falta estimation_method
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 422

    def test_invalid_json(self, client):
        """Test de error por JSON inválido."""
        response = client.post(
            "/frequency/fit",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_design_event_missing_parameters(self, client):
        """Test de error por parámetros faltantes."""
        request = {
            "distribution_name": "Normal",
            # Falta parameters
            "return_period": 100.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 422


class TestAPIResponseFormat:
    """Tests del formato de respuesta de la API."""

    def test_fit_response_json_serializable(self, client):
        """Test de que la respuesta es JSON serializable."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "MOM",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 200
        # Si la respuesta es válida, el JSON ya fue parseado correctamente
        data = response.json()
        assert isinstance(data, dict)

    def test_design_event_response_json_serializable(self, client):
        """Test de que la respuesta de evento de diseño es JSON serializable."""
        request = {
            "distribution_name": "Normal",
            "parameters": {"mu": 100.0, "sigma": 20.0},
            "return_period": 100.0,
        }

        response = client.post("/frequency/design-event", json=request)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_content_type_header(self, client):
        """Test de que la API retorna Content-Type correcto."""
        request = {
            "series": [100.0, 120.0, 95.0, 110.0, 105.0],
            "estimation_method": "MOM",
        }

        response = client.post("/frequency/fit", json=request)

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
